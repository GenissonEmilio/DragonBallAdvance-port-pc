/* USA 0x0810B22C: 164 complete bytes match the ROM. */
#include "audio.h"
#include "hardware.h"
void Sound_SetFrequency(DbaaU32 mode) {
  register struct SoundInfo *sound __asm__("r4");
  register DbaaU32 input __asm__("r2") = mode;
  int index;
  int samples;
  __asm__("" : "+r"(input));
  {
    register struct SoundInfo **address __asm__("r0") = &gSoundInfoPointer;
    __asm__("" : "+r"(address));
    sound = *address;
    __asm__("" : "+r"(sound));
  }
  input = (input & 0xF0000) >> 16;
  __asm__("" : "+r"(input));
  index = input;
  sound->frequency = index;
  {
    register const DbaaU16 *table __asm__("r1") = gSoundSamplesPerFrame;
    register DbaaU32 offset __asm__("r0");
    __asm__("" : "+r"(table));
    offset = index - 1;
    __asm__("" : "+r"(offset));
    offset <<= 1;
    __asm__("" : "+r"(offset));
    offset += (DbaaU32)table;
    __asm__("" : "+r"(offset));
    samples = *(const DbaaU16 *)offset;
  }
  sound->samplesPerFrame = samples;
  sound->pcmFrames = 1584 / samples;
  {
    register int rate __asm__("r1") = (597275 * samples + 5000) / 10000;
    __asm__("" : "+r"(rate));
    sound->sampleRate = rate;
    sound->sampleReciprocal = ((0x01000000 / rate) + 1) >> 1;
  }
  IO16(0x04000102) = 0;
  IO16(0x04000100) = -(280896 / samples);
  Sound_VSyncOn();
  while (*(volatile DbaaU8 *)0x04000006 == 159)
    ;
  while (*(volatile DbaaU8 *)0x04000006 != 159)
    ;
  IO16(0x04000102) = 0x80;
}
