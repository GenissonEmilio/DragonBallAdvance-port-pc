/* Native game entry and verified audio/IRQ bindings. Generated game functions
 * keep GBA addresses in uint32_t; indirect calls resolve to host C functions.
 */
#include "audio_helpers.h"
#include "audio_runtime.h"
#ifdef DBAA_GAME_AUDIO_ENABLED
#include "game_audio.h"
#endif
#include "game_runtime.h"
#include "gba/display.h"
#include "gba/gba_runtime.h"
#include "irq_dispatch.h"
#include <stdio.h>
#include <stdlib.h>

#ifndef GBA_NATIVE_ONLY
#error This bridge requires a runtime built without the ARM interpreter.
#endif

static uint64_t audio_calls, irq_calls, fallback_failures;
static uint64_t null_callbacks, indirect_calls;
static int rom_validated;

static void native_fail(const char *reason, uint32_t target) {
  ++fallback_failures;
  fprintf(stderr, "[native failure] %s: target=%08X pc=%08X lr=%08X sp=%08X\n",
          reason, target, r[15], r[14], r[13]);
  exit(1);
}

static uint32_t host_read(void *user, uint32_t a, uint32_t n) {
  (void)user;
  /* ROM prefetch makes ordinary RAM/I/O data accesses free in the generated
   * code's timing model: instruction fetches normally advance that clock.
   * Native services must charge work too, particularly polled VCOUNT waits. */
  cpu_fetches(a == 0x04000006 ? 3 : 1);
  if (n == 1)
    return bus_read8(a);
  if (n == 2)
    return bus_read16(a);
  if (n == 4)
    return bus_read32(a);
  native_fail("invalid native read width", a);
  return 0;
}
static void host_write(void *user, uint32_t a, uint32_t value, uint32_t n) {
  (void)user;
  cpu_fetches(1);
  if (n == 1)
    bus_write8(a, (uint8_t)value);
  else if (n == 2)
    bus_write16(a, (uint16_t)value);
  else if (n == 4)
    bus_write32(a, value);
  else
    native_fail("invalid native write width", a);
}
static uint32_t host_call(void *user, uint32_t target, uint32_t a, uint32_t b,
                          uint32_t c) {
  (void)user;
  (void)a;
  (void)b;
  (void)c;
  native_fail("unbound native audio service", target);
  return 0;
}
static const DbaaMusicHost audio_host = {NULL, host_read, host_write,
                                         host_call};

static void native_audio(uint32_t target) {
  uint32_t saved_lr = r[14];
  ++audio_calls;
  r[0] = Dbaa_AudioCall(&audio_host, target, r[0], r[1], r[2]);
  r[15] = saved_lr & ~1u;
}
#define DBAA_AUDIO_ENTRY(name, address)                                        \
  void func_##name(void) { native_audio(address); }
#include "game_audio_entries.inc"
#undef DBAA_AUDIO_ENTRY

void func_0810A6D8(void) {
  uint32_t saved_lr = r[14];
  ++audio_calls;
  Dbaa_AudioVBlank(&audio_host);
#ifdef DBAA_GAME_AUDIO_ENABLED
  Dbaa_GameAudioVBlank();
#endif
  r[15] = saved_lr & ~1u;
}

/* The original GamePak IRQ loops permanently; report it instead of hiding it.
 * All ordinary callbacks retain the IRQ dispatcher's register/flag protocol. */
void gba_native_ram_dispatch(uint32_t target) {
  if (target == 0x03001F50) {
    DbaaIrqSelection choice;
    ++irq_calls;
    if (Dbaa_IrqSelect(&audio_host, target, &choice))
      native_fail("GamePak IRQ permanent loop in original ROM", target);
    r[0] = choice.target;
    r[1] = choice.table_address;
    r[2] = choice.table_offset;
    r[3] = 0x04000200;
    CPU_N = CPU_C = false;
    CPU_Z = choice.acknowledged == 0;
    cpu_bx(choice.target);
    return;
  }
  native_fail("unregistered code entry; no ARM interpreter is compiled",
              target);
}

#define DBAA_GAME_ENTRY(name, address) void func_##name(void);
#include "game_extra_entries.inc"
#undef DBAA_GAME_ENTRY
static void (*extra_lookup(uint32_t target))(void) {
#define DBAA_GAME_ENTRY(name, address)                                         \
  if (target == address)                                                       \
    return func_##name;
#include "game_extra_entries.inc"
#undef DBAA_GAME_ENTRY
  return NULL;
}

/* Strongly replaces the generated dispatcher: unknown calls cannot become
 * silent no-ops or invoke an interpreter. Null callbacks are intentional. */
void cpu_bx(uint32_t target) {
  ++indirect_calls;
  if (target == 0 || target == 1) {
    ++null_callbacks;
    return;
  }
  if (g_bx_depth >= 512)
    native_fail("indirect call depth exceeded", target);
  if ((target >> 24) == 2 || (target >> 24) == 3) {
    gba_native_ram_dispatch(target);
    return;
  }
  void (*fn)(void) = extra_lookup(target);
  uint32_t declared = target;
  if (!fn) {
    fn = recomp_lookup_fn(target & ~1u);
    declared = recomp_lookup(target & ~1u);
  }
  if (!fn || declared != target)
    native_fail("unregistered ROM entry or instruction-set mismatch", target);
  ++g_bx_depth;
  fn();
  --g_bx_depth;
}

extern void dbaa_generated_background_queue(void);
void func_0810DDCC(void) {
  uint32_t sp = r[13], lr = r[14];
  dbaa_generated_background_queue();
  if (g_ret < 0x08000000 || r[13] != sp) {
    fprintf(stderr,
            "[background return] in sp=%08X lr=%08X; out sp=%08X lr=%08X "
            "ret=%08X r0=%08X pc=%08X\n",
            sp, lr, r[13], r[14], g_ret, r[0], r[15]);
  }
}

/* Analyzer-created missing block: reaching it must fail, never skip logic. */
void func_07FFFC30(void) { native_fail("missing generated block", 0x07FFFC30); }

static int validate_rom(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f)
    return 0;
  uint32_t crc = UINT32_MAX;
  size_t n = 0;
  int ch;
  while ((ch = fgetc(f)) != EOF) {
    ++n;
    crc ^= (unsigned)ch;
    for (unsigned i = 0; i < 8; ++i)
      crc = (crc >> 1) ^ ((0u - (crc & 1u)) & 0xEDB88320u);
  }
  int ok = !ferror(f) && n == 0x1000000 && ~crc == 0x7D7306DFu;
  fclose(f);
  return ok;
}

static void native_report(void) {
  const char *path = getenv("DBAA_NATIVE_REPORT");
  FILE *f = path ? fopen(path, "wb") : stderr;
  if (!f) {
    perror("native report");
    return;
  }
  fprintf(f,
          "{\n \"rom_validated\":%s,\n \"frames\":%u,\n \"audio_calls\":%llu,\n"
          " \"irq_calls\":%llu,\n \"indirect_calls\":%llu,\n"
          " \"null_callbacks\":%llu,\n \"fallback_failures\":%llu,\n"
          " \"cpu_interpreter_compiled\":false,\n "
          "\"whole_game_validated\":false\n}\n",
          rom_validated ? "true" : "false", Dbaa_GameFrameCount(),
          (unsigned long long)audio_calls, (unsigned long long)irq_calls,
          (unsigned long long)indirect_calls,
          (unsigned long long)null_callbacks,
          (unsigned long long)fallback_failures);
  if (path)
    fclose(f);
}

extern void game_entry(void);
int main(int argc, char **argv) {
  const char *path = display_parse_args(argc, argv);
  if (!path)
    path = "baserom.gba";
  if (!validate_rom(path)) {
    fprintf(stderr, "Requires the exact USA BDVE rev0 ROM (CRC32 7d7306df).\n");
    return 2;
  }
  const char *validate = getenv("GBA_VALIDATE");
  if (validate && atoi(validate)) {
    fprintf(stderr,
            "Interpreter-based validation belongs in the separate oracle.\n");
    return 2;
  }
  rom_validated = 1;
  atexit(native_report);
#ifdef DBAA_GAME_AUDIO_ENABLED
  const char *device = getenv("DBAA_GAME_AUDIO_DEVICE");
  int device_enabled = device ? atoi(device) != 0 : !display_headless();
  if (!Dbaa_GameAudioInit(device_enabled)) {
    fprintf(stderr, "[audio failure] %s\n", Dbaa_GameAudioError());
    return 1;
  }
#endif
  gba_init(path);
  gba_run(game_entry);
  native_fail("game entry returned unexpectedly", r[15]);
  return 1;
}
