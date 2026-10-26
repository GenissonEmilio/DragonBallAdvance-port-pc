/* USA 0x0810C124: 20 complete linked bytes match; C/GNU C only. */
#include "audio.h"
extern void (*gSoundCommands[])(struct MusicPlayer *, struct MusicTrack *);
void MusicEvent_ExtendedEnd(struct MusicPlayer *player,
                            struct MusicTrack *track) {
  void (*fn)(struct MusicPlayer *, struct MusicTrack *) = gSoundCommands[0];
  fn(player, track);
}
