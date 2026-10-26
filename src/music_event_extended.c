/* USA 0x0810C104: 32 complete linked bytes match; C/GNU C only. */
#include "audio.h"
extern void (*const gMusicExtendedCommands[])(struct MusicPlayer *,
                                              struct MusicTrack *);
void MusicEvent_Extended(struct MusicPlayer *player, struct MusicTrack *track) {
  DbaaU32 n = *track->command;
  track->command++;
  gMusicExtendedCommands[n](player, track);
}
