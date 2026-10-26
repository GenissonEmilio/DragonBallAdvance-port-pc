/* USA 0x0810C194: 20 complete linked bytes match; C/GNU C only. */
#include "audio.h"
void MusicEvent_Attack(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register DbaaU32 value __asm__("r2");
  register DbaaU8 *destination __asm__("r0");
  __asm__("" : "+r"(track));
  value = **(const DbaaU8 **)(track + 0x40);
  __asm__("" : "+r"(value));
  destination = track + 0x2c;
  __asm__("" : "+r"(destination));
  *destination = value;
  (*(const DbaaU8 **)(track + 0x40))++;
}
