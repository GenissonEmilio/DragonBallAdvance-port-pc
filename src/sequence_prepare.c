#include "sequences.h"
/* USA 0x080C8964: 104 complete bytes match the ROM. */
void Sequence_Prepare(void) {
  struct DbaaSequenceData *data = SEQUENCE_DATA(gCurrentTask);
  DbaaSequenceInitializer init = gSequenceInitializers[data->sequenceId];
  if (init == 0)
    gCurrentTask->callback = Sequence_Finish;
  else {
    init(&data->vram, data, &data->counter);
    gCurrentTask->callback = Sequence_Run;
  }
}
