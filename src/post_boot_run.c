#include "backgrounds.h"
#include "post_boot.h"
/* USA 0x080EE6DC: 308 complete bytes match the ROM. */
void PostBoot_Run(void) {
  struct DbaaPostBootData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaPostBootData);
  DbaaU8 bg;
  DbaaU16 zeroA, zeroB, zeroC;
  gGameHalf03002BEC = 0x400;
  gGamePointer03002CB0 = (void *)0x06010000;
  Func_08113C38();
  gDisplayControlShadow = 0x1040;
  gBgControlShadow[0] = 0x5E00;
  gBgControlShadow[1] = 0x5C04;
  gBgControlShadow[2] = 0x5A08;
  for (bg = 0; bg < 4; bg++) {
    gBackgroundScroll[bg][0] = 0;
    gBackgroundScroll[bg][1] = 0;
  }
  gBlendShadow[0] = 0;
  gBlendShadow[1] = 0;
  gBlendShadow[2] = 0;
  zeroA = 0;
  Bios_CpuSet(&zeroA, (void *)0x06000000, 0x0100C000);
  zeroB = 0;
  Bios_CpuSet(&zeroB, gBgPaletteBuffer, 0x01000100);
  zeroC = 0;
  Bios_CpuSet(&zeroC, gObjPaletteBuffer, 0x01000100);
  gSystemFlags |= 3;
  MusicPlayer_Stop(gPostBootMusicPlayer);
  Music_StartSong(1);
  PostBoot_PrepareSprites(data);
  data->phase = PostBoot_Begin;
  gCurrentTask->callback = PostBoot_Update;
}
