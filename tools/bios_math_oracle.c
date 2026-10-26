/* Full mGBA only in this test process. No BIOS or ROM downloaded. */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <mgba/gba/core.h>
#include <mgba/internal/gba/gba.h>
#include <mgba/internal/gba/bios.h>
#include <mgba/internal/arm/arm.h>
#include <mgba-util/vfs.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

static void quiet(struct mLogger *l, int cat, enum mLogLevel level,
                  const char *format, va_list args) {
  (void)l; (void)cat; (void)level; (void)format; (void)args;
}

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  static struct mLogger logger;
  logger.log = quiet;
  mLogSetDefaultLogger(&logger);
  FILE *input = fopen(argv[1], "rb"), *output = fopen(argv[2], "wb");
  if (!input || !output) return 1;
  struct mCore *core = GBACoreCreate();
  if (!core || !core->init(core)) return 1;
  static mColor pixels[240 * 160];
  core->setVideoBuffer(core, pixels, 240);
  struct VFile *rom = VFileOpen(argv[3], O_RDONLY);
  if (!rom || !core->loadROM(core, rom)) return 1;
  mCoreConfigInit(&core->config, "dbaa-bios-math-oracle");
  mCoreConfigSetDefaultIntValue(&core->config, "skipBios", 1);
  mCoreConfigSetDefaultIntValue(&core->config, "useBios", 0);
  core->loadConfig(core, &core->config);
  core->reset(core);
  struct GBA *gba = core->board;
  uint32_t row[5];
  unsigned count = 0;
  while (fread(row, sizeof(row), 1, input) == 1) {
    memcpy(gba->cpu->gprs, row+1, 4*sizeof(uint32_t));
    GBASwi16(gba->cpu, (int)row[0]);
    if (fwrite(gba->cpu->gprs, 4*sizeof(uint32_t), 1, output) != 1) return 1;
    ++count;
  }
  int ok = !ferror(input) && feof(input);
  ok &= !fclose(input); ok &= !fclose(output);
  core->deinit(core);
  printf("%u BIOS math register cases\n", count);
  return ok ? 0 : 1;
}
