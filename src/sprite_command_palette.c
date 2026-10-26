/* USA 0x08110048: 148 complete bytes match the ROM. */
#include "sprites.h"
struct PaletteCommand {
  int command, index;
  DbaaU16 count, offset;
};
int SpriteCommand_Palette(const int *words, struct DbaaPostBootSprite *sprite) {
  const struct PaletteCommand *command = (const struct PaletteCommand *)words;
  sprite->animationCursor += 3;
  if (!(sprite->flags & 0x40000)) {
    int index = command->index;
    DbaaU32 flags = gSystemFlags;
    if (flags & 0x20000) {
      Graphics_LoadObjPalette(
          (const DbaaU8 *)gSpriteTables->palettes + (index << 5),
          (sprite->palette << 4) + (DbaaU8)command->offset, command->count);
    } else {
      volatile DbaaU32 *dma = (volatile DbaaU32 *)0x040000D4;
      dma[0] =
          (DbaaU32)((const DbaaU8 *)gSpriteTables->palettes + (index << 5));
      dma[1] = (DbaaU32)gObjPaletteBuffer +
               (((sprite->palette << 4) + command->offset) << 1);
      dma[2] = 0x80000000 | command->count;
      (void)dma[2];
      gSystemFlags = flags | 2;
    }
  }
  return 1;
}
