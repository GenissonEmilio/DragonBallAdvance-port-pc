#include "post_boot.h"
/* USA 0x080EFB34: 92 complete bytes match the ROM. */
void PostBoot_Begin(struct DbaaPostBootData *data) {
  gDisplayControlShadow |= 0x2000;
  gWindowShadow[0] = 0xFF;
  gWindowShadow[2] = 0x2080;
  gWindowShadow[4] = 0x3F;
  gWindowShadow[5] = 0;
  PostBoot_LoadBackground(0);
  PostBoot_LoadBackground(1);
  PostBoot_LoadBackground(2);
  PostBoot_LoadTiles(8);
  data->phase = PostBoot_EnableBackgrounds;
  gDisplayControlShadow |= 0x2000;
}
