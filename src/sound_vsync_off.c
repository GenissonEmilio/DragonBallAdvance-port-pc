/* USA 0x0810B3BC: 124 complete bytes match the ROM. */
#include "audio.h"
#include "graphics.h"
void Sound_VSyncOff(void) {
  struct SoundInfo *sound = gSoundInfoPointer;
  DbaaU32 lock = sound->lock;
  DbaaU32 zero;
  if (lock - 0x68736D53U > 1)
    return;
  sound->lock = lock + 10;
  if (IO32(0x040000C4) & 0x02000000)
    IO32(0x040000C4) = 0x84400004;
  if (IO32(0x040000D0) & 0x02000000)
    IO32(0x040000D0) = 0x84400004;
  IO16(0x040000C6) = 0x400;
  IO16(0x040000D2) = 0x400;
  zero = 0;
  Bios_CpuSet(&zero, (DbaaU8 *)sound + 0x350, 0x05000318);
}
