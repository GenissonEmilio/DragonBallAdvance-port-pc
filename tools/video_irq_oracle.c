/* Pinned full mGBA as hardware-event reference only. No CPU instruction runs. */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <mgba/gba/core.h>
#include <mgba/internal/gba/gba.h>
#include <mgba/internal/gba/io.h>
#include <mgba/internal/arm/arm.h>
#include <mgba-util/vfs.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
static void quiet(struct mLogger *l, int c, enum mLogLevel level, const char *f, va_list a) {
  (void)l; (void)c; (void)level; (void)f; (void)a;
}
static void next_frame(struct GBA *gba) {
  unsigned frame = gba->video.frameCounter;
  while (gba->video.frameCounter == frame) mTimingTick(&gba->timing, 1);
}
int main(int n, char **v) {
  if (n != 3) return 2;
  static struct mLogger logger;
  logger.log = quiet; mLogSetDefaultLogger(&logger);
  struct mCore *core = GBACoreCreate();
  if (!core || !core->init(core)) return 1;
  static mColor pixels[240 * 160];
  core->setVideoBuffer(core, pixels, 240);
  struct VFile *rom = VFileOpen(v[1], O_RDONLY);
  if (!rom || !core->loadROM(core, rom)) return 1;
  mCoreConfigInit(&core->config, "dbaa-video-irq-oracle");
  mCoreConfigSetDefaultIntValue(&core->config, "skipBios", 1);
  mCoreConfigSetDefaultIntValue(&core->config, "useBios", 0);
  core->loadConfig(core, &core->config); core->reset(core);
  struct GBA *gba = core->board;
  gba->cpu->cycles = 0;
  mTimingTick(&gba->timing, 0); /* attach the reset event list */
  unsigned mode = (unsigned)strtoul(v[2], NULL, 10);
  GBAIOWrite(gba, 0x200, 0); GBAIOWrite(gba, 0x208, 0); GBAIOWrite(gba, 0x202, 0xFFFF);
  GBAIOWrite(gba, 0x004, (127u << 8) | ((mode < 8 ? mode : 0) << 3));
  next_frame(gba);
  unsigned first = gba->memory.io[0x202/2] & 7u, late = 0, next = 0, disabled = 0;
  if (mode == 8) {
    GBAIOWrite(gba, 0x202, 0xFFFF); GBAIOWrite(gba, 0x004, (127u << 8) | 8);
    for (unsigned i = 0; i < 15; ++i) mTimingTick(&gba->timing, 1);
    late = gba->memory.io[0x202/2] & 7u;
    next_frame(gba); next = gba->memory.io[0x202/2] & 7u;
    GBAIOWrite(gba, 0x004, 127u << 8); GBAIOWrite(gba, 0x202, 0xFFFF);
    next_frame(gba); disabled = gba->memory.io[0x202/2] & 7u;
  }
  if (mode == 9 || mode == 10) {
    if (mode == 10) for (unsigned i = 0; i < 1101; ++i) mTimingTick(&gba->timing, 1);
    first = gba->memory.io[0x004/2];
    GBAIOWrite(gba, 0x004, 0xFF00); late = gba->memory.io[0x004/2];
    GBAIOWrite(gba, 0x004, 0x7FFF); next = gba->memory.io[0x004/2];
  }
  if (mode == 11) {
    GBAIOWrite(gba, 0x202, 0xFFFF); GBAIOWrite(gba, 0x004, (160u << 8) | 0x20);
    first = gba->memory.io[0x004/2]; late = gba->memory.io[0x202/2] & 7u;
    GBAIOWrite(gba, 0x202, 0xFFFF); GBAIOWrite(gba, 0x004, (160u << 8) | 0x20);
    next = gba->memory.io[0x202/2] & 7u;
    GBAIOWrite(gba, 0x004, (161u << 8) | 0x20); GBAIOWrite(gba, 0x004, (160u << 8) | 0x20);
    disabled = gba->memory.io[0x202/2] & 7u;
  }
  if (mode == 12) {
    while (gba->video.vcount != 227) mTimingTick(&gba->timing, 1);
    first = gba->memory.io[0x004/2] & 7u;
    while (gba->video.vcount != 0) mTimingTick(&gba->timing, 1);
    late = gba->memory.io[0x004/2] & 7u;
  }
  if (mode == 13) {
    first = gba->memory.io[0x006/2];
    GBAIOWrite(gba, 0x006, 37); late = gba->memory.io[0x006/2];
  }
  core->deinit(core);
  printf("%u %u %u %u %u\n", mode, first, late, next, disabled);
  return 0;
}
