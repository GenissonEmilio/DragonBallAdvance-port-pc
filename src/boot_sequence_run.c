#include "backgrounds.h"
#include "sequences.h"
/* USA 0x080F2FD0: 252 complete bytes match the ROM. */
void BootSequence_Run(void) {
  struct DbaaBootSequenceData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaBootSequenceData);
  DbaaU8 bg;
  DbaaU16 zeroA, zeroB, zeroC;
  gDisplayControlShadow = 0x140;
  gBgControlShadow[0] = 0x1F00;
  for (bg = 0; bg < 4; bg++) {
    gBackgroundScroll[bg][0] = 0;
    gBackgroundScroll[bg][1] = 0;
  }
  gBlendShadow[0] = 0xFF;
  gBlendShadow[1] = 0;
  gBlendShadow[2] = 16;
  zeroA = 0;
  Bios_CpuSet(&zeroA, (void *)0x06000000, 0x0100C000);
  zeroB = 0;
  Bios_CpuSet(&zeroB, gBgPaletteBuffer, 0x01000100);
  zeroC = 0;
  Bios_CpuSet(&zeroC, gObjPaletteBuffer, 0x01000100);
  gSystemFlags |= 3;
  Func_0810AEEC();
  gCurrentTask->callback = BootSequence_Update;
  data->phase = BootSequence_StartScreen;
}
