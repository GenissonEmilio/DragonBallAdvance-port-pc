/* USA 0x08111CE8: 8 complete bytes match the ROM. */
#include "sprites.h"
/* The ROM preserves incoming r0 as the result of command -10. */
int SpriteCommand_Reserved9(const int *command,
                            struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 4;
  return (int)command;
}
