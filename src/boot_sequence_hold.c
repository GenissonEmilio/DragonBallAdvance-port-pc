#include "sequences.h"
/* USA 0x080F3518: 48 complete bytes match the ROM. */
void BootSequence_Hold(struct DbaaBootSequenceData *data) {
  data->timer++;
  if (data->flags & 1)
    BootSequence_BeginFadeOut(data);
  if (data->timer >= data->duration)
    BootSequence_BeginFadeOut(data);
}
