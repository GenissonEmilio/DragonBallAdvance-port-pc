/* USA 0x0810B474: 120 complete bytes match the ROM. */
#include "audio.h"
void MusicPlayer_Open(struct MusicPlayer *player, void *data,
                      DbaaU32 rawCount) {
  register struct MusicTrack *track __asm__("r6") = data;
  struct SoundInfo *sound;
  DbaaU8 count;
  __asm__("" : "+r"(track));
  count = rawCount;
  if (!count)
    return;
  if (count > 16)
    count = 16;
  sound = gSoundInfoPointer;
  if (sound->lock != 0x68736D53)
    return;
  sound->lock++;
  MusicPlayer_Clear(player);
  player->tracks = track;
  player->trackCount = count;
  player->status = 0x80000000;
  while (count) {
    track->status = 0;
    count--;
    track++;
  }
  if (sound->playerMain) {
    player->nextPlayerMain = sound->playerMain;
    player->nextPlayer = sound->firstPlayer;
    sound->playerMain = 0;
  }
  sound->firstPlayer = player;
  sound->playerMain = MusicPlayer_Update;
  sound->lock = 0x68736D53;
  player->lock = 0x68736D53;
}
