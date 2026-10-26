/* USA 0x0810AFF0: 280 complete bytes match the ROM. */
#include "audio.h"
#include "graphics.h"
extern void (*gSoundCommands[36])(void);
void SoundCommand_BFAC(void);
void SoundCommand_AC68(void);
void SoundCommand_AC7C(void);
void SoundCommand_C104(void);
void SoundCommand_AC00(void);
void SoundCommand_B610(void);
void SoundCommand_B6D8(void);
void Cgb_Update(void);
/* Absolute linker value 0: preserve the original literal load of maxLines. */
extern const DbaaU8 gSoundDefaultMaxLines;
void Sound_Extend(void *data) {
  DbaaU8 *channels = data;
  struct SoundInfo *sound;
  DbaaU32 lock, zero;
  register volatile DbaaU16 *stereo __asm__("r3");
  IO16(0x04000084) = 0x8F;
  stereo = (volatile DbaaU16 *)0x04000080;
  __asm__("" : "+r"(stereo));
  *stereo = 0;
  *(volatile DbaaU8 *)0x04000063 = 8;
  *(volatile DbaaU8 *)0x04000069 = 8;
  *(volatile DbaaU8 *)0x04000079 = 8;
  *(volatile DbaaU8 *)0x04000065 = 0x80;
  *(volatile DbaaU8 *)0x0400006D = 0x80;
  *(volatile DbaaU8 *)0x0400007D = 0x80;
  *(volatile DbaaU8 *)0x04000070 = 0;
  *(volatile DbaaU8 *)stereo = 0x77;
  sound = gSoundInfoPointer;
  lock = sound->lock;
  if (lock != 0x68736D53)
    return;
  sound->lock = lock + 1;
  gSoundCommands[8] = SoundCommand_BFAC;
  gSoundCommands[17] = SoundCommand_AC68;
  gSoundCommands[19] = SoundCommand_AC7C;
  gSoundCommands[28] = SoundCommand_C104;
  gSoundCommands[29] = SoundCommand_AC00;
  gSoundCommands[30] = (void (*)(void))Sound_SetFrequency;
  gSoundCommands[31] = (void (*)(void))MusicTrack_Stop;
  gSoundCommands[32] = SoundCommand_B610;
  gSoundCommands[33] = SoundCommand_B6D8;
  sound->cgbChannels = channels;
  sound->cgbMain = Cgb_Update;
  sound->stopCgb = Cgb_Stop;
  sound->callback30 = (void (*)(void))Cgb_CalculateFrequency;
  sound->maxLines = (DbaaU32)&gSoundDefaultMaxLines;
  zero = 0;
  Bios_CpuSet(&zero, channels, 0x05000040);
  channels[1] = 1;
  channels[0x1C] = 0x11;
  channels[0x41] = 2;
  channels[0x5C] = 0x22;
  channels[0x81] = 3;
  channels[0x9C] = 0x44;
  {
    DbaaU8 *last = channels + 0xC0;
    last[1] = 4;
    last[0x1C] = 0x88;
  }
  sound->lock = lock;
}
