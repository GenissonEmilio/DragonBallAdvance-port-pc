/* NONMATCHING ARM C candidate for the SDK's private r2/r3 filter ABI. */
#include "audio.h"
void Sound_FilterAddress(void);
void MusicEvent_Voice(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register DbaaU32 *source __asm__("r2");
  register DbaaU32 value __asm__("r3");
  DbaaU8 *command = *(DbaaU8 **)(track + 0x40);
  DbaaU32 index = *command;
  *(DbaaU8 **)(track + 0x40) = command + 1;
  source = (DbaaU32 *)(index * 12);
  __asm__ volatile("" : "+r"(source));
  value = *(DbaaU32 *)((DbaaU8 *)player + 0x30);
  __asm__ volatile("" : "+r"(value));
  source = (DbaaU32 *)((DbaaU32)source + value);
  value = source[0];
  __asm__ volatile("" : "+r"(track), "+r"(source), "+r"(value));
  Sound_FilterAddress();
  __asm__ volatile("" : "=r"(track), "=r"(source), "=r"(value));
  *(DbaaU32 *)(track + 0x24) = value;
  value = source[1];
  __asm__ volatile("" : "+r"(source), "+r"(value));
  Sound_FilterAddress();
  __asm__ volatile("" : "=r"(track), "=r"(source), "=r"(value));
  *(DbaaU32 *)(track + 0x28) = value;
  value = source[2];
  __asm__ volatile("" : "+r"(source), "+r"(value));
  Sound_FilterAddress();
  __asm__ volatile("" : "=r"(track), "=r"(value));
  *(DbaaU32 *)(track + 0x2C) = value;
}
