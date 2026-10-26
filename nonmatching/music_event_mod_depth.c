/* NONMATCHING ARM C: native C and exact GBA assembly are separate.
 * The SDK byte helper leaves its result in r3 rather than r0. */
#include "audio.h"
void Music_ReadCommandByte(void *player, DbaaU8 *track);
void Music_ClearModulation(void *player, DbaaU8 *track);
void MusicEvent_ModDepth(void *player, DbaaU8 *track) {
  register DbaaU32 value __asm__("r3");
  Music_ReadCommandByte(player, track);
  __asm__ volatile("" : "=r"(value));
  track[0x17] = value;
  if (!value)
    Music_ClearModulation(player, track);
}
