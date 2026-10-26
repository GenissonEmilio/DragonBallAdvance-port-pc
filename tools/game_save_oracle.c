/* Reference process only. Runs the original ROM with the pinned full mGBA
 * core and exports its EEPROM. Never linked into the native executable. */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <mgba/gba/core.h>
#include <mgba/internal/gba/gba.h>
#include <mgba-util/vfs.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

static void quiet(struct mLogger *l, int cat, enum mLogLevel level,
                  const char *format, va_list arguments) {
  (void)l; (void)cat; (void)level; (void)format; (void)arguments;
}
int main(int argc, char **argv) {
  if (argc != 5 && argc != 6)
    return 2; /* rom, frames, save-out, memory-out, optional save-in */
  static struct mLogger logger;
  logger.log = quiet;
  mLogSetDefaultLogger(&logger);
  struct mCore *core = GBACoreCreate();
  if (!core || !core->init(core))
    return 1;
  static mColor video[240 * 160];
  core->setVideoBuffer(core, video, 240);
  struct VFile *rom = VFileOpen(argv[1], O_RDONLY);
  if (!rom || !core->loadROM(core, rom))
    return 1;
  mCoreConfigInit(&core->config, "dbaa-save-oracle");
  mCoreConfigSetDefaultIntValue(&core->config, "skipBios", 1);
  mCoreConfigSetDefaultIntValue(&core->config, "useBios", 0);
  core->loadConfig(core, &core->config);
  core->reset(core);
  if (argc == 6) {
    FILE *input = fopen(argv[5], "rb");
    unsigned char bytes[8192];
    if (!input)
      return 1;
    size_t size = fread(bytes, 1, sizeof(bytes), input);
    int ok = !ferror(input) && (size == 512 || size == 8192);
    fclose(input);
    if (!ok || !core->savedataRestore(core, bytes, size, false))
      return 1;
  }
  unsigned frames = (unsigned)strtoul(argv[2], NULL, 10);
  for (unsigned i = 0; i < frames; ++i) {
    core->setKeys(core, 0);
    core->runFrame(core);
  }
  void *save = NULL;
  size_t size = core->savedataClone(core, &save);
  FILE *output = fopen(argv[3], "wb");
  int ok = output && save && size && fwrite(save, 1, size, output) == size;
  if (output)
    ok &= !fclose(output);
  free(save);
  struct GBA *gba = core->board;
  output = fopen(argv[4], "wb");
  if (!output)
    return 1;
  ok &= fwrite(gba->memory.wram, 1, 0x40000, output) == 0x40000;
  ok &= fwrite(gba->memory.iwram, 1, 0x8000, output) == 0x8000;
  ok &= !fclose(output);
  core->deinit(core);
  printf("{\"ok\":%s,\"frames\":%u,\"save_bytes\":%zu,\"original_rom_executed\":true}\n",
         ok ? "true" : "false", frames, size);
  return ok ? 0 : 1;
}
