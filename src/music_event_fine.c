/* USA 0x0810A4E4: 48 complete bytes match; empty constraints only. */
#include "audio.h"
void Audio_UnlinkChannel(struct SoundChannel *channel);
void MusicEvent_Fine(struct MusicPlayer *player, struct MusicTrack *track) {
  register struct MusicTrack *owner __asm__("r5") = track;
  register struct SoundChannel *channel __asm__("r4");
  __asm__ volatile("" : "+r"(owner));
  channel = owner->channel;
  __asm__ volatile("" : "+r"(channel));
  if (!channel)
    goto finish;
  do {
    register DbaaU32 status __asm__("r1") = channel->status;
    register DbaaU32 mask __asm__("r0") = 0xC7;
    __asm__ volatile("" : "+r"(status), "+r"(mask));
    if (mask & status) {
      mask = 0x40;
      __asm__ volatile("" : "+r"(mask));
      status |= mask;
      channel->status = status;
    }
    Audio_UnlinkChannel(channel);
    channel = channel->next;
  } while (channel);
finish:
  {
    register DbaaU32 zero __asm__("r0") = 0;
    __asm__ volatile("" : "+r"(zero));
    owner->status = zero;
  }
}
