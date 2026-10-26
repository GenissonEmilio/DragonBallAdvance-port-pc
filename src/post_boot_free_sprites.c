#include "post_boot.h"
/* USA 0x080F054C: 48 complete bytes match the ROM. */
void PostBoot_FreeSprites(struct DbaaPostBootData *data) {
  DbaaU8 i;
  for (i = 0; i < 9; i++) {
    struct DbaaPostBootSprite *sprite = &data->sprites[i];
    if (sprite->vram) {
      Vram_FreeTiles(sprite->vram);
      sprite->vram = 0;
    }
  }
}
