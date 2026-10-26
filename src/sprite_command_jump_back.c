/* USA 0x08111C78: 12 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_JumpBack(const int *command,
                           struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor -= command[1];
  return 1;
}
