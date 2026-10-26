#include "sequences.h"
/* USA 0x080F357C: 48 complete bytes match the ROM. */
void BootSequence_BeginPause(struct DbaaBootSequenceData *data) {
  DbaaU16 duration;
  data->timer = 0;
  duration = data->script[data->screen].pauseFrames;
  if (data->flags & 1)
    duration >>= 1;
  data->duration = duration;
  data->phase = BootSequence_Advance;
}
