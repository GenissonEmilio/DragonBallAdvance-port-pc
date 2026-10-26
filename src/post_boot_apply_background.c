#include "backgrounds.h"
#include "post_boot.h"
/* USA 0x080EF1E0: 80 complete bytes match the ROM. */
void PostBoot_ApplyBackground(DbaaU8 index) {
  const struct DbaaPostBootBackground *entry = &gPostBootBackgrounds[index];
  DbaaU8 bg = entry->background;
  gBgControlShadow[bg] &= 0xFFFC;
  gBgControlShadow[bg] |= entry->priority;
  gBackgroundScroll[bg][0] = entry->scrollX;
  gBackgroundScroll[bg][1] = entry->scrollY;
}
