/* USA 0x0810A554: 32 complete linked bytes match; C/GNU C only. */
/* SDK byte reader preserves r0/r1 and returns the filtered low byte in r3. */
#include "audio.h"
void Sound_ReadByteFiltered(void);
void MusicEvent_Goto(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register const DbaaU8 *command __asm__("r2");
  register DbaaU32 value __asm__("r0"), byte __asm__("r3");
  __asm__("" : "+r"(track));
  command = *(const DbaaU8 **)(track + 0x40);
  __asm__("" : "+r"(command));
  value = command[3];
  value <<= 8;
  byte = command[2];
  value |= byte;
  value <<= 8;
  byte = command[1];
  value |= byte;
  value <<= 8;
  __asm__ volatile("" : : "r"(value), "r"(track), "r"(command));
  Sound_ReadByteFiltered();
  __asm__ volatile("" : "=r"(value), "=r"(byte), "=r"(track));
  value |= byte;
  *(DbaaU32 *)(track + 0x40) = value;
}
