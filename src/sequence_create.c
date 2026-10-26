#include "sequences.h"
/* USA 0x080C863C: 328 complete bytes match the ROM. */
#define CLEAR_CHAR_BASE(index_)                                                \
  {                                                                            \
    zero = 0;                                                                  \
    DMA_START(&zero,                                                           \
              (void *)(0x06000000 + ((gBgControlShadow[index_] & 0xC) << 12)), \
              0x85000010);                                                     \
  }

void Func_080C863C(DbaaU16 id, DbaaU8 step, DbaaU8 mode,
                   DbaaTaskCallback onComplete) {
  struct DbaaTask *task;
  register struct DbaaSequenceData *data __asm__("r2");
  DbaaU32 zero;
  /* Empty constraints retain the original zero/base register flow. */
  {
    register DbaaU32 value __asm__("r2") = 0;
    __asm__("" : : "r"(value));
    gSequenceContext.skipRequested = value;
  }
  task = Task_Create(Sequence_Prepare, 0x14, 0x200, 0x10, Sequence_OnDestroy);
  {
    register struct DbaaSequenceData *resolved __asm__("r0");
    if (task->flags & 0x10) {
      DbaaU32 offset = task->dataOffset * 4;
      register DbaaU32 base __asm__("r1") = 0x02000000;
      __asm__("" : "+r"(base));
      resolved = (void *)(offset + base);
    } else {
      DbaaU32 offset = task->dataOffset;
      register DbaaU32 base __asm__("r0") = 0x03000000;
      __asm__("" : "+r"(base));
      resolved = (void *)(offset + base);
    }
    data = resolved;
  }
  data->state = 0;
  data->firstStep = step;
  data->nextStep = step + 1;
  data->sequenceId = id;
  data->completionMode = mode;
  data->counter = 0;
  data->vram = (void *)0x06010000;
  data->onComplete = onComplete;
  if (gSequenceClearFlags[data->sequenceId]) {
    gDisplayControlShadow = 0;
    CLEAR_CHAR_BASE(0);
    CLEAR_CHAR_BASE(1);
    CLEAR_CHAR_BASE(2);
    gBgClearValues[2] = 0;
    gBgClearRects.data[2][0] = 0;
    gBgClearRects.data[2][1] = 0;
    gBgClearRects.data[2][2] = 255;
    gBgClearRects.data[2][3] = 64;
    gBgClearValues[1] = 0;
    gBgClearRects.data[1][0] = 0;
    gBgClearRects.data[1][1] = 0;
    gBgClearRects.data[1][2] = 255;
    gBgClearRects.data[1][3] = 64;
    gBgClearValues[0] = 0;
    gBgClearRects.data[0][0] = 0;
    gBgClearRects.data[0][1] = 0;
    gBgClearRects.data[0][2] = 255;
    gBgClearRects.data[0][3] = 64;
    zero = 0;
    Bios_CpuFastSet(&zero, (void *)0x06000000, 0x01006000);
  }
}
