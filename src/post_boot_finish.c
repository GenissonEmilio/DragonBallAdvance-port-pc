#include "post_boot.h"
/* USA 0x080EE8EC: 164 complete bytes match the ROM. */
void PostBoot_Finish(void) {
  struct DbaaPostBootData *data =
      (struct DbaaPostBootData *)SEQUENCE_DATA(gCurrentTask);
  DbaaU16 zero;
  gDisplayControlShadow &= 0xDFFF;
  {
    DbaaU16 *source = &zero;
    /* Keep the zero-cell address before the fill. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, gWindowShadow, 0x01000006);
  }
  gDbaaGameState.word14++;
  PostBoot_FreeSprites(data);
  gGameHalf03002BEC = 0x200;
  gGamePointer03002CB0 = (void *)0x06014000;
  Func_08113C38();
  data->sequence->state--;
  Task_Destroy(gCurrentTask);
}
