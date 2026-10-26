#include "sequences.h"
/* USA 0x080F30CC: 140 complete bytes match the ROM. */
void BootSequence_Finish(void) {
  struct DbaaBootSequenceData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaBootSequenceData);
  DbaaU16 zeroA, zeroB;
  gBlendShadow[0] = 0;
  gBlendShadow[1] = 0;
  gBlendShadow[2] = 0;
  zeroA = 0;
  Bios_CpuSet(&zeroA, gBgPaletteBuffer, 0x01000100);
  zeroB = 0;
  Bios_CpuSet(&zeroB, gObjPaletteBuffer, 0x01000100);
  gSystemFlags |= 3;
  data->sequence->state--;
  Task_Destroy(gCurrentTask);
}
