/* NONMATCHING ARM C: the SDK uses an interior reader entry and r3 result. */
#include "audio.h"
void Music_ReadCommandFilteredFromPointer(DbaaU8 *destination, DbaaU8 *track,
                                          DbaaU8 *source);
void MusicEvent_Port(void *player, DbaaU8 *input) {
  register DbaaU8 *source __asm__("r2");
  register DbaaU8 *destination __asm__("r0");
  register DbaaU32 value __asm__("r3");
  (void)player;
  source = *(DbaaU8 **)(input + 0x40);
  value = *source++;
  destination = (DbaaU8 *)(0x04000060 + value);
  Music_ReadCommandFilteredFromPointer(destination, input, source);
  __asm__ volatile("" : "=r"(destination), "=r"(value));
  *destination = value;
}
