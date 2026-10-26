#include "sequences.h"
/* USA 0x080F33F4: 112 complete bytes match the ROM. */
void BootSequence_Update(void) {
  struct DbaaBootSequenceData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaBootSequenceData);
  if (data->screen && (gPressedKeys & 0xB))
    data->flags |= 1;
  data->phase(data);
  if (data->flags < 0)
    gCurrentTask->callback = BootSequence_Finish;
}
