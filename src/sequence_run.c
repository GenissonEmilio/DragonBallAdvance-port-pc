#include "sequences.h"
/* USA 0x080C8784: 196 complete bytes match the ROM. */
void Sequence_Run(void) {
  struct DbaaSequenceData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaSequenceData);
  data->counter++;
  if (data->sequenceId != 0x46 && (gPressedKeys & 8)) {
    if (gSequenceContext.flags & 0x40) {
      if (!(gSequenceContext.flags & 0x20080)) {
        gSequenceContext.flags |= 0x80;
        Func_0800C0C8(4);
        gWindowShadow[0] = 0;
        gWindowShadow[2] = 0;
        gWindowShadow[1] = 0;
        gWindowShadow[3] = 0;
        gWindowShadow[4] = 0;
        gWindowShadow[5] = 0;
        gDisplayControlShadow &= 0x9FFF;
        data->counter = 10000;
        gSequenceContext.skipRequested = 1;
        return;
      }
    } else {
      data->counter = 10000;
      gSequenceContext.skipRequested = 1;
    }
  }
  if (data->state == 0)
    gCurrentTask->callback = Sequence_Finish;
}
