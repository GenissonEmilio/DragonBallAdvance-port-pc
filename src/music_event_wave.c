/* USA 0x0810C138: 72 complete linked bytes match; C/GNU C only. */
/* The captured r4 seed is fully overwritten by the four byte insertions. */
#include "audio.h"
void MusicEvent_Wave(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register const DbaaU8 *command __asm__("r2");
  register DbaaU32 value __asm__("r4"), byte __asm__("r0"),
      shifted __asm__("r3");
  __asm__("" : "+r"(track));
  command = *(const DbaaU8 **)(track + 0x40);
  __asm__("" : "+r"(command));
  __asm__("" : "=r"(value));
  value &= 0xFFFFFF00;
  __asm__("" : "+r"(value));
  byte = command[0];
  __asm__("" : "+r"(byte));
  value |= byte;
  byte = command[1];
  __asm__("" : "+r"(byte));
  shifted = byte << 8;
  __asm__("" : "+r"(shifted));
  value &= 0xFFFF00FF;
  __asm__("" : "+r"(value));
  value |= shifted;
  byte = command[2];
  __asm__("" : "+r"(byte));
  shifted = byte << 16;
  __asm__("" : "+r"(shifted));
  value &= 0xFF00FFFF;
  __asm__("" : "+r"(value));
  value |= shifted;
  byte = command[3];
  __asm__("" : "+r"(byte));
  shifted = byte << 24;
  __asm__("" : "+r"(shifted));
  value &= 0x00FFFFFF;
  __asm__("" : "+r"(value));
  value |= shifted;
  *(DbaaU32 *)(track + 0x28) = value;
  *(const DbaaU8 **)(track + 0x40) = command + 4;
}
