/* Test process only: execute the original ROM through pinned full mGBA.
 * Ordinary controller inputs only. Never linked into the native port. */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <mgba/gba/core.h>
#include <mgba/internal/gba/gba.h>
#include <mgba/internal/arm/arm.h>
#include <mgba-util/vfs.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef DBAA_TEST_CONTROLLER
#include "campaign_controller.h"
#endif

static struct GBA *trace_gba;
static unsigned trace_frame, trace_from = UINT32_MAX, trace_to;
static void (*prior_store32)(struct ARMCore *, uint32_t, int32_t, int *);
static void counter_store32(struct ARMCore *cpu, uint32_t a, int32_t value, int *cycles) {
  if (a == 0x030030D4 && trace_frame >= trace_from && trace_frame <= trace_to) {
    fprintf(stderr, "COUNTER call=%u frame=%u v=%d c=%u value=%u pc=%08X\n",
            trace_frame, trace_gba->video.frameCounter, trace_gba->video.vcount,
            (uint32_t)mTimingCurrentTime(&trace_gba->timing), (uint32_t)value, (uint32_t)cpu->gprs[15]);
  }
  prior_store32(cpu, a, value, cycles);
}
static void quiet(struct mLogger *l, int cat, enum mLogLevel level,
                  const char *format, va_list args) {
  (void)l; (void)cat; (void)level;
  if (trace_gba && trace_frame >= trace_from && trace_frame <= trace_to && !strncmp(format, "SWI:", 4)) {
    fprintf(stderr, "ORACLE call=%u frame=%u v=%d c=%u game=%u rng=%08X ", trace_frame,
            trace_gba->video.frameCounter, trace_gba->video.vcount,
            (uint32_t)mTimingCurrentTime(&trace_gba->timing), trace_gba->memory.iwram[0x30D4/4],
            trace_gba->memory.iwram[0x6C50/4]);
    vfprintf(stderr, format, args);
    fputc('\n', stderr);
  }
}
static uint32_t word(const unsigned char *ram, unsigned o) {
  return (uint32_t)ram[o] | (uint32_t)ram[o+1] << 8 |
         (uint32_t)ram[o+2] << 16 | (uint32_t)ram[o+3] << 24;
}
int main(int argc, char **argv) {
  if (argc != 8 && argc != 9) return 2;
  /* rom, frames, input, observations, save-out, memory-out, image-out,
   * optional save-in. input event N is applied before reference frame N+1. */
  FILE *input = fopen(argv[3], "r"), *obs = fopen(argv[4], "wb");
  if (!input || !obs) return 1;
  static struct mLogger logger;
  logger.log = quiet;
  mLogSetDefaultLogger(&logger);
  const char *trace = getenv("DBAA_ORACLE_SWI_LOG");
  if (trace) sscanf(trace, "%u,%u", &trace_from, &trace_to);
  struct mCore *core = GBACoreCreate();
  if (!core || !core->init(core)) return 1;
  static mColor pixels[240 * 160];
  core->setVideoBuffer(core, pixels, 240);
  struct VFile *rom = VFileOpen(argv[1], O_RDONLY);
  if (!rom || !core->loadROM(core, rom)) return 1;
  mCoreConfigInit(&core->config, "dbaa-campaign-oracle");
  mCoreConfigSetDefaultIntValue(&core->config, "skipBios", 1);
  mCoreConfigSetDefaultIntValue(&core->config, "useBios", 0);
  core->loadConfig(core, &core->config);
  core->reset(core);
  if (argc == 9) {
    FILE *seed = fopen(argv[8], "rb");
    unsigned char bytes[8192];
    if (!seed) return 1;
    size_t n = fread(bytes, 1, sizeof(bytes), seed);
    int ok = !ferror(seed) && (n == 512 || n == 8192);
    fclose(seed);
    if (!ok || !core->savedataRestore(core, bytes, n, false)) return 1;
  }
  struct GBA *gba = core->board;
  trace_gba = gba;
  if (trace && *trace) {
    prior_store32 = gba->cpu->memory.store32;
    gba->cpu->memory.store32 = counter_store32;
  }
  const unsigned char *ram = (const unsigned char *)gba->memory.wram;
  unsigned total = (unsigned)strtoul(argv[2], NULL, 10), keys = 0;
  unsigned next_frame = 0, next_keys = 0;
  int have_next = fscanf(input, "%u %x", &next_frame, &next_keys) == 2;
  unsigned non_single_frame_calls = 0;
  fprintf(obs, "frame,x256,y256,camera_x,camera_y,state_00,state_08,keys,rng,scheduler_frame,cycles\n");
  for (unsigned i = 0; i < total; ++i) {
    trace_frame = i+1;
    while (have_next && next_frame <= i) {
      keys = next_keys;
      have_next = fscanf(input, "%u %x", &next_frame, &next_keys) == 2;
    }
    unsigned applied = keys;
#ifdef DBAA_TEST_CONTROLLER
    applied = Dbaa_TestCampaignKeys(ram, (const uint8_t *)gba->memory.iwram, i+1, applied);
#endif
    core->setKeys(core, applied);
    unsigned prior_frame = gba->video.frameCounter;
    core->runFrame(core);
    if (gba->video.frameCounter - prior_frame != 1) ++non_single_frame_calls;
    fprintf(obs, "%u,%d,%d,%u,%u,%u,%u,%u,%u,%u,%u\n", i+1,
              (int32_t)word(ram, 0x205C4), (int32_t)word(ram, 0x205C8),
              word(ram, 0x29EE8), word(ram, 0x29EEC), word(ram, 0x29F30),
              word(ram, 0x29F38), applied, word((const unsigned char *)gba->memory.iwram, 0x6C50),
              gba->video.frameCounter, (uint32_t)mTimingCurrentTime(&gba->timing));
  }
  fclose(input);
  int ok = !fclose(obs);
  void *save = NULL;
  size_t size = core->savedataClone(core, &save);
  FILE *f = fopen(argv[5], "wb");
  ok &= f && save && size && fwrite(save, 1, size, f) == size;
  if (f) ok &= !fclose(f);
  free(save);
  f = fopen(argv[6], "wb");
  if (!f) return 1;
  ok &= fwrite(gba->memory.wram, 1, 0x40000, f) == 0x40000;
  ok &= fwrite(gba->memory.iwram, 1, 0x8000, f) == 0x8000;
  ok &= fwrite(gba->memory.io, 1, 0x400, f) == 0x400;
  ok &= fwrite(gba->video.palette, 1, 0x400, f) == 0x400;
  ok &= fwrite(gba->video.vram, 1, 0x18000, f) == 0x18000;
  ok &= fwrite(&gba->video.oam, 1, 0x400, f) == 0x400;
  ok &= !fclose(f);
  f = fopen(argv[7], "wb");
  if (!f) return 1;
  fprintf(f, "P6\n240 160\n255\n");
  for (unsigned i = 0; i < 240 * 160; ++i) {
    unsigned char rgb[3] = { pixels[i] & 255, (pixels[i] >> 8) & 255, (pixels[i] >> 16) & 255 };
    ok &= fwrite(rgb, 1, 3, f) == 3;
  }
  ok &= !fclose(f);
  unsigned video_frames = gba->video.frameCounter;
  core->deinit(core);
  printf("{\"ok\":%s,\"frames\":%u,\"save_bytes\":%zu,\"original_rom_executed\":true,"
         "\"video_frames\":%u,\"non_single_frame_calls\":%u}\n",
         ok ? "true" : "false", total, size, video_frames, non_single_frame_calls);
  return ok ? 0 : 1;
}
