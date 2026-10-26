/* USA 0x0810FFB8: 144 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Tiles(const int *command, struct DbaaPostBootSprite *sprite) {
  const DbaaU8 *source;
  DbaaU16 size;
  sprite->animationCursor += 3;
  if (!(sprite->flags & 0x80000)) {
    int index = command[1];
    /* Preserve the ROM signed index; do not take its absolute value. */
    if (index < 0) {
      source = gSpriteTables->tiles8 + (index << 6);
      size = command[2] << 6;
    } else {
      source = gSpriteTables->tiles4 + (index << 5);
      size = command[2] << 5;
    }
    gVramTransferQueue[gVramQueueWriteIndex].source = (DbaaU32)source;
    gVramTransferQueue[gVramQueueWriteIndex].destination =
        (DbaaU32)sprite->vram;
    gVramTransferQueue[gVramQueueWriteIndex].size = size;
    gVramQueueWriteIndex = (gVramQueueWriteIndex + 1) & 0x7F;
  }
  return 1;
}
