/* USA 0x0810A4C4: 32 complete bytes match; empty constraints only. */
#include "audio.h"
void Audio_UnlinkChannel(struct SoundChannel *channel) {
  register struct SoundChannel *ch __asm__("r0") = channel;
  register struct MusicTrack *track __asm__("r3") = ch->track;
  register struct SoundChannel *next __asm__("r1");
  register struct SoundChannel *previous __asm__("r2");
  __asm__ volatile("" : "+r"(track));
  if (!track)
    goto end;
  next = ch->next;
  __asm__ volatile("" : "+r"(next));
  previous = *(struct SoundChannel **)((DbaaU8 *)ch + 0x30);
  __asm__ volatile("" : "+r"(previous));
  if (previous)
    previous->next = next;
  else
    track->channel = next;
  if (next)
    *(struct SoundChannel **)((DbaaU8 *)next + 0x30) = previous;
  next = 0;
  __asm__ volatile("" : "+r"(next));
  ch->track = (void *)next;
end:;
}
