/* NONMATCHING ARM C: SDK preserves r1 and returns the filtered byte in r3. */
#include "audio.h"
void Music_ReadCommandFiltered(void *player, DbaaU8 *track);
void MusicEvent_BendRange(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1");
  register DbaaU32 value __asm__("r3"), flags __asm__("r2");
  Music_ReadCommandFiltered(player, input);
  __asm__ volatile("" : "=r"(track), "=r"(value));
  track[0x0F] = value;
  value = track[0];
  flags = 12;
  __asm__("" : "+r"(flags));
  value |= flags;
  track[0] = value;
}
