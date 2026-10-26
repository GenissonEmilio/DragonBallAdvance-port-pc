/* USA 0x08111D0C: 16 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Order(const int *command, struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 2;
  sprite->order = command[1] << 6;
  return 1;
}
