#include "audio.h"
void MusicPlayer_Stop(struct MusicPlayer *player) {
  int i;
  struct MusicTrack *track;
  if (player->lock != 0x68736D53)
    return;
  player->lock++;
  player->status |= 0x80000000;
  i = player->trackCount;
  track = player->tracks;
  while (i > 0) {
    MusicTrack_Stop(player, track);
    i--;
    track++;
  }
  player->lock = 0x68736D53;
}
