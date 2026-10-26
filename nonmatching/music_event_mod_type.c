/* NONMATCHING ARM C: SDK preserves r1 and returns the filtered byte in r3. */
#include "audio.h"
void Music_ReadCommandFiltered(void *player, DbaaU8 *track);
void MusicEvent_ModType(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1");
  register DbaaU32 value __asm__("r3"), old __asm__("r0"), flags __asm__("r2");
  Music_ReadCommandFiltered(player, input);
  __asm__ volatile("" : "=r"(track), "=r"(value));
  old = track[0x18];
  __asm__("" : "+r"(old));
  if (old != value) {
    track[0x18] = value;
    value = track[0];
    flags = 15;
    __asm__("" : "+r"(flags));
    value |= flags;
    track[0] = value;
  }
}
