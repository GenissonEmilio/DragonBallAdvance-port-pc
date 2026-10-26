/* USA 0x0810B120: 20 complete bytes match the ROM. */
#include "audio.h"
void MusicPlayer_Clear(struct MusicPlayer *player) {
  gMusicPlayerClearCallback(player);
}
