#include "sequences.h"
/* USA 0x080C88F0: 116 complete bytes match the ROM. */
void Sequence_Finish(void) {
  struct DbaaSequenceData *data = SEQUENCE_DATA(gCurrentTask);
  DbaaU8 mode = data->completionMode;
  DbaaTaskCallback onComplete = data->onComplete;
  *(DbaaU16 *)gBgPaletteBuffer = 0;
  gSystemFlags |= 1;
  Task_Destroy(gCurrentTask);
  if (mode != 12) {
    if (onComplete == 0)
      gSequenceCompletionCallbacks[mode]();
    else
      onComplete();
  }
}
