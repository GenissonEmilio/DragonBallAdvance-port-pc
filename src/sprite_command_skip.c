/* USA 0x08111CC4: 12 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Skip(const int *command, struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 3;
  return 1;
}
