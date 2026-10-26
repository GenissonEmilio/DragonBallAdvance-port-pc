/* USA 0x08111CD0: 24 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Switch(const int *command,
                         struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 2;
  sprite->animation = ((const DbaaU16 *)command)[2];
  sprite->previousVariant = 255;
  sprite->variant = ((const DbaaU16 *)command)[3];
  return -1;
}
