/* USA 0x08111CA8: 28 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Translate(const int *command,
                            struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 2;
  sprite->x += ((const DbaaU16 *)command)[2];
  sprite->y += ((const DbaaU16 *)command)[3];
  return 1;
}
