#include "sequences.h"
/* USA 0x080F34F8: 32 complete bytes match the ROM. */
void BootSequence_BeginHold(struct DbaaBootSequenceData *data) {
  data->timer = 0;
  data->duration = data->script[data->screen].holdFrames;
  data->phase = BootSequence_Hold;
}
