#include "sequences.h"
/* USA 0x080F3158: 80 complete bytes match the ROM. */
void BootSequence_BeginFadeOut(struct DbaaBootSequenceData *data) {
  gBlendShadow[0] = 0xFF;
  gBlendShadow[1] = 0;
  gBlendShadow[2] = 0;
  data->timer = 0;
  if (data->flags & 1)
    data->duration = data->script[data->screen].fadeOutFrames >> 1;
  else
    data->duration = data->script[data->screen].fadeOutFrames;
  data->phase = BootSequence_FadeOut;
}
