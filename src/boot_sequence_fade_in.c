#include "sequences.h"
/* USA 0x080F34A8: 80 complete bytes match the ROM. */
void BootSequence_FadeIn(struct DbaaBootSequenceData *data) {
  data->timer++;
  gBlendShadow[2] = 16 - (data->timer << 4) / data->duration;
  if (data->timer >= data->duration) {
    gBlendShadow[2] = 0;
    if (data->flags & 1)
      BootSequence_BeginFadeOut(data);
    else
      BootSequence_BeginHold(data);
  }
}
