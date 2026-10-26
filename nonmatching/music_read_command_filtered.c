#include "audio.h"
void Music_ReadCommandFiltered(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register const DbaaU8 *command __asm__("r2");
  register DbaaU32 value __asm__("r3");
  __asm__("" : "+r"(track));
  command = *(const DbaaU8 **)(track + 0x40);
  __asm__("" : "+r"(command));
  value = (DbaaU32)(command + 1);
  __asm__("" : "+r"(value));
  *(DbaaU32 *)(track + 0x40) = value;
  value = *command;
  if ((DbaaU32)command < 0x02000000)
    value = 0;
  __asm__ volatile("" : "+r"(value));
}
