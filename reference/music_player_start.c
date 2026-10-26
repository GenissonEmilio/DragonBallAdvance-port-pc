/* Readable behavioral reference only; excluded from the byte-matching build. */
#include "audio.h"
#include "services.h"
void MusicPlayer_Start(struct MusicPlayer *player, const void *header) {
  const struct DbaaSongHeader *song = header;
  int i;
  struct MusicTrack *track;
  DbaaU8 priority;
  if (player->lock != 0x68736D53)
    return;
  priority = song->priority;
  if (player->priority &&
      ((player->song && (player->tracks->status & 0x40)) ||
       ((DbaaU16)player->status && (int)player->status >= 0))) {
    priority = song->priority;
    if (player->songPriority > priority)
      return;
  }
  player->lock++;
  player->status = 0;
  player->song = song;
  player->voicegroup = song->voicegroup;
  player->songPriority = priority;
  player->clock = 0;
  player->tempo = 150;
  player->tempoInterval = 150;
  player->tempoScale = 256;
  player->tempoCounter = 0;
  player->fadeInterval = 0;
  i = 0;
  track = player->tracks;
  while (i < song->trackCount && i < player->trackCount) {
    MusicTrack_Stop(player, track);
    track->status = 0xC0;
    track->channel = 0;
    track->command = song->trackData[i];
    i++;
    track++;
  }
  while (i < player->trackCount) {
    MusicTrack_Stop(player, track);
    track->status = 0;
    i++;
    track++;
  }
  if (song->mode & 0x80)
    Func_0810B2D0(song->mode);
  player->lock = 0x68736D53;
}
