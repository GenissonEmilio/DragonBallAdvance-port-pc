/* USA 0x08111CF0: 28 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Priority(const int *command,
                           struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 2;
  sprite->flags = (sprite->flags & ~0x3000) | (command[1] << 12);
  return 1;
}
