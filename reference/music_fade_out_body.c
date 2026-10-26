/* Readable algorithm reference: NONMATCHING and excluded from production. */
#include "audio.h"
void Music_FadeOutBody(struct MusicPlayer *player) {
  DbaaU16 level;
  int count;
  struct MusicTrack *track;
  if (!player->fadeInterval)
    return;
  player->fadeCounter--;
  if (player->fadeCounter)
    return;
  player->fadeCounter = player->fadeInterval;
  if (player->fadeLevel & 2) {
    player->fadeLevel += 16;
    if (player->fadeLevel >= 256) {
      player->fadeLevel = 256;
      player->fadeInterval = 0;
    }
  } else {
    player->fadeLevel -= 16;
    if ((DbaaS16)player->fadeLevel <= 0) {
      count = player->trackCount;
      track = player->tracks;
      while (count > 0) {
        MusicTrack_Stop(player, track);
        level = player->fadeLevel;
        if (!(level & 1))
          track->status = 0;
        count--;
        track++;
      }
      if (player->fadeLevel & 1)
        player->status |= 0x80000000;
      else
        player->status = 0x80000000;
      player->fadeInterval = 0;
      return;
    }
  }
  count = player->trackCount;
  track = player->tracks;
  while (count > 0) {
    if (track->status & 0x80) {
      level = player->fadeLevel;
      track->volumePublic = level >> 2;
      track->status |= 3;
    }
    count--;
    track++;
  }
}
