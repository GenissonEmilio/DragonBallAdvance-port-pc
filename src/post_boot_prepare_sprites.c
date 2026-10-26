#include "post_boot.h"
/* USA 0x080EF3B4: 148 complete bytes match the ROM. */
void PostBoot_PrepareSprites(struct DbaaPostBootData *data) {
  DbaaU8 i;
  for (i = 0; i < 9; i++) {
    struct DbaaPostBootSprite *sprite = &data->sprites[i];
    register const struct DbaaPostBootSpriteConfig *entry __asm__("r4") = ({
      register const struct DbaaPostBootSpriteConfig *base __asm__("r0") =
          gPostBootSpriteConfig;
      /* Retain the per-sprite base/index ordering without instructions. */
      __asm__("" : "+r"(base) : "r"(i));
      (const struct DbaaPostBootSpriteConfig *)((DbaaU32)i * 8 + (DbaaU32)base);
    });
    sprite->vram = Vram_AllocateTiles(entry->tiles);
    sprite->order = 0x400;
    sprite->animation = entry->animation;
    sprite->variant = entry->variant;
    sprite->animationDelay = 0;
    sprite->previousVariant = 0xFF;
    sprite->speed = 0x10;
    sprite->palette = entry->palette;
    sprite->x = -64;
    sprite->y = -64;
    sprite->flags = 0;
    switch (i) {
    case 0:
      sprite->flags = 0x400;
      break;
    case 1:
      sprite->order = 0x440;
      break;
    }
    Func_0810FD70(sprite);
  }
}
