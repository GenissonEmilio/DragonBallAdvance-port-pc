#include "backgrounds.h"
#include "post_boot.h"
/* USA 0x080EF230: 108 complete bytes match the ROM. */
void PostBoot_LoadSpecialBackground(DbaaU8 index) {
  const struct DbaaPostBootBackground *entry = &gPostBootBackgrounds[index];
  DbaaU8 bg = entry->background;
  gBgControlShadow[bg] &= 0xFFFC;
  gBgControlShadow[bg] |= entry->priority;
  PostBoot_LoadSpecialTiles((gBgControlShadow[bg] >> 2) & 3);
  PostBoot_LoadSpecialMap((gBgControlShadow[bg] >> 8) & 31,
                          entry->sourcePalette);
  PostBoot_LoadSpecialPalette(entry->sourcePalette);
  gBackgroundScroll[bg][0] = entry->scrollX;
  gBackgroundScroll[bg][1] = entry->scrollY;
}
