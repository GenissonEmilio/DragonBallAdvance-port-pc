/* NONMATCHING ARM C: SDK preserves r1 and returns the filtered byte in r3. */
#include "audio.h"
void Music_ReadCommandFiltered(void *player, DbaaU8 *track);
void MusicEvent_LfoDelay(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1");
  register DbaaU32 value __asm__("r3");
  Music_ReadCommandFiltered(player, input);
  __asm__ volatile("" : "=r"(track), "=r"(value));
  track[0x1B] = value;
}
