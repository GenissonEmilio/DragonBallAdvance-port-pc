#include "sequences.h"
/* USA 0x080F3548: 52 complete bytes match the ROM. */
void BootSequence_FadeOut(struct DbaaBootSequenceData *data) {
  data->timer++;
  gBlendShadow[2] = (data->timer << 4) / data->duration;
  if (data->timer >= data->duration)
    BootSequence_BeginPause(data);
}
