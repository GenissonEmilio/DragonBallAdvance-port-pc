/* USA 0x0810B134: 248 complete bytes match the ROM. */
#include "audio.h"
#include "graphics.h"
extern void (*gSoundCommands[36])(void);
void Sound_CopyCommandTable(void (**destination)(void));
void Sound_UpdateTrack(void);
void Sound_Dummy(void);
void Sound_Initialize(void *data) {
  struct SoundInfo *sound = data;
  DbaaU32 zero;
  sound->lock = 0;
  if (IO32(0x040000C4) & 0x02000000)
    IO32(0x040000C4) = 0x84400004;
  if (IO32(0x040000D0) & 0x02000000)
    IO32(0x040000D0) = 0x84400004;
  IO16(0x040000C6) = 0x400;
  IO16(0x040000D2) = 0x400;
  IO16(0x04000084) = 0x8F;
  IO16(0x04000082) = 0xA90E;
  *(volatile DbaaU8 *)0x04000089 =
      (*(volatile DbaaU8 *)0x04000089 & 0x3F) | 0x40;
  IO32(0x040000BC) = (DbaaU32)sound + 0x350;
  IO32(0x040000C0) = 0x040000A0;
  IO32(0x040000C8) = (DbaaU32)sound + 0x980;
  IO32(0x040000CC) = 0x040000A4;
  gSoundInfoPointer = sound;
  zero = 0;
  Bios_CpuSet(&zero, sound, 0x050003EC);
  sound->channels = 8;
  sound->volume = 15;
  sound->callback38 = Sound_UpdateTrack;
  sound->cgbMain = Sound_Dummy;
  sound->stopCgb = (void (*)(DbaaU8))Sound_Dummy;
  sound->callback30 = Sound_Dummy;
  sound->callback3C = Sound_Dummy;
  Sound_CopyCommandTable(gSoundCommands);
  sound->commands = gSoundCommands;
  Sound_SetFrequency(0x40000);
  sound->lock = 0x68736D53;
}
