#include "audio.h"
/* USA 0x0810A98C. GCC 3.4.6 is an alternative matching compiler for this
 * originally assembly-style library routine. Ten empty constraints retain
 * register lifetimes; no instruction templates are embedded.
 * The named section requests zero assembler alignment; the linker places its
 * complete contents in executable ROM .text at the original address. */

__attribute__((section(".data"))) void
MusicTrack_Stop(struct MusicPlayer *player, struct MusicTrack *track) {
  register struct MusicTrack *owner __asm__("r5") = track;
  register struct SoundChannel *channel __asm__("r4");
  register DbaaU32 zero __asm__("r6");
  register DbaaU32 flags __asm__("r1");
  register DbaaU32 mask __asm__("r0");
  __asm__ volatile("" : "+r"(owner));
  flags = owner->status;
  __asm__ volatile("" : "+r"(flags));
  mask = 0x80;
  __asm__ volatile("" : "+r"(mask));
  if (!(mask & flags))
    goto end;
  channel = owner->channel;
  __asm__ volatile("" : "+r"(channel));
  if (!channel)
    goto clear_owner;
  zero = 0;
  __asm__ volatile("" : : "r"(zero));
  do {
    {
      register DbaaU32 status __asm__("r0") = channel->status;
      __asm__ volatile("" : : "r"(status));
      if (status) {
        register DbaaU32 type __asm__("r0") = channel->type;
        register DbaaU32 channelMask __asm__("r3");
        __asm__ volatile("" : : "r"(type));
        channelMask = 7;
        __asm__ volatile("" : : "r"(channelMask));
        type &= channelMask;
        if (type) {
          register void (*callback)(DbaaU8) __asm__("r3") =
              gSoundInfoPointer->stopCgb;
          __asm__ volatile("" : : "r"(type), "r"(callback));
          callback(type);
        }
        channel->status = zero;
      }
    }
    channel->track = (void *)zero;
    channel = channel->next;
  } while (channel);
clear_owner:
  __asm__ volatile("" : "+r"(channel));
  owner->channel = channel;
end:;
}
