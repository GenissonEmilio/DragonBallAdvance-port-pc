#include "post_boot.h"
/* USA 0x080F0874: 36 complete bytes match the ROM. */
void PostBoot_RingDraw(struct DbaaPostBootRingData *data) {
  struct DbaaPostBootSprite *sprites = data->sprites;
  DbaaU8 i;
  for (i = 0; i < 7; i++)
    Graphics_DrawSprite(&sprites[i]);
}
