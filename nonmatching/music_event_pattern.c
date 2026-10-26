#include "audio.h"
void MusicEvent_Goto(void *, DbaaU8 *);
void MusicEvent_Fine(void *, DbaaU8 *);
void MusicEvent_Pattern(void *player, DbaaU8 *track) {
  unsigned depth = track[2];
  if (depth < 3) {
    *(const DbaaU8 **)(track + 0x44 + depth * 4) =
        *(const DbaaU8 **)(track + 0x40) + 4;
    track[2]++;
    MusicEvent_Goto(player, track);
  } else
    MusicEvent_Fine(player, track);
}
