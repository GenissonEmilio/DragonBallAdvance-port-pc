/* USA 0x08111C94: 20 complete bytes match the ROM. */
#include "audio.h"
#include "sprites.h"
int SpriteCommand_Sound(const int *command, struct DbaaPostBootSprite *sprite) {
  sprite->animationCursor += 2;
  Music_StartSong(((const DbaaU16 *)command)[2]);
  return 1;
}
