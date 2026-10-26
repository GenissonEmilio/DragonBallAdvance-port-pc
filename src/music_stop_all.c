#include "audio.h"
void Func_0810AEEC(void) {
  int i;
  for (i = 0; i < (DbaaU16)(DbaaU32)&gMusicPlayerCount; i++)
    MusicPlayer_Stop(gMusicPlayerTable[i].player);
}
