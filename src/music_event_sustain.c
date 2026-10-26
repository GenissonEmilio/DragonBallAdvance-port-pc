/* USA 0x0810C1BC: 20 complete linked bytes match; C/GNU C only. */
#include "audio.h"
void MusicEvent_Sustain(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register DbaaU32 value __asm__("r0");
  register DbaaU8 *destination __asm__("r2");
  __asm__("" : "+r"(track));
  value = **(const DbaaU8 **)(track + 0x40);
  __asm__("" : "+r"(value));
  destination = track + 0x2e;
  __asm__("" : "+r"(destination));
  *destination = value;
  (*(const DbaaU8 **)(track + 0x40))++;
}
