#include "sequences.h"
/* USA 0x080C8898: 72 complete bytes match the ROM. */
extern DbaaU8 gBackgroundReadIndex, gBackgroundWriteIndex, gBgSpriteCount;
extern DbaaU8 gVramQueueReadIndex, gVramQueueWriteIndex;
void Sequence_StartAfterBoot(void) {
  Tasks_DestroyPriorityRange(0, 0xFFFF);
  gBackgroundReadIndex = gBackgroundWriteIndex;
  gBgSpriteCount = 0;
  gVramQueueReadIndex = gVramQueueWriteIndex;
  Func_080C863C(0x4D, 0, 1, 0);
}
