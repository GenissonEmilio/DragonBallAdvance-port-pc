/* USA 0x08111C84: 16 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_End(const int *command, struct DbaaPostBootSprite *sprite) {
  sprite->flags |= 0x4000;
  return 0;
}
