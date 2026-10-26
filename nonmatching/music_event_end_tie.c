/* NONMATCHING ARM C: original leaf frame is retained in separate assembly.
 * Native production C is in port/audio/audio_helpers.c. */
#include "audio.h"
void MusicEvent_EndTie(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register DbaaU8 *command __asm__("r2");
  register DbaaU32 key __asm__("r3"), status __asm__("r2");
  register DbaaU32 active __asm__("r4"), releasing __asm__("r5"),
      value __asm__("r0");
  __asm__("" : "+r"(track));
  command = *(DbaaU8 **)(track + 0x40);
  __asm__("" : "+r"(command));
  key = *command;
  __asm__("" : "+r"(key));
  if (key >= 0x80)
    goto reuse_key;
  track[5] = key;
  command++;
  __asm__("" : "+r"(command));
  *(DbaaU8 **)(track + 0x40) = command;
  goto channels;
reuse_key:
  key = track[5];
channels:
  track = *(DbaaU8 **)(track + 0x20);
  __asm__("" : "+r"(track));
  if (!track)
    goto done;
  active = 0x83;
  releasing = 0x40;
  __asm__("" : "+r"(active), "+r"(releasing));
loop:
  status = track[0];
  __asm__("" : "+r"(status));
  if (!(status & active))
    goto next;
  if (status & releasing)
    goto next;
  value = track[0x11];
  __asm__("" : "+r"(value));
  if (value != key)
    goto next;
  value = 0x40;
  __asm__("" : "+r"(value));
  status |= value;
  track[0] = status;
  goto done;
next:
  track = *(DbaaU8 **)(track + 0x34);
  __asm__("" : "+r"(track));
  if (track)
    goto loop;
done:;
}
