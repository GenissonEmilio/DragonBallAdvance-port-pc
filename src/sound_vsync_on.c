/* USA 0x0810B438: 60 complete bytes match the ROM. */
#include "audio.h"
#include "hardware.h"
void Sound_VSyncOn(void) {
  struct SoundInfo *sound = gSoundInfoPointer;
  DbaaU32 lock = sound->lock;
  if (lock != 0x68736D53) {
    IO16(0x040000C6) = 0xB600;
    IO16(0x040000D2) = 0xB600;
    (void)*(volatile DbaaU8 *)&sound->unknown04;
    sound->unknown04 = 0;
    sound->lock = lock - 10;
  }
}
