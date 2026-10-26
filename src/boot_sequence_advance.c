#include "sequences.h"
/* USA 0x080F31A8: 120 complete bytes match the ROM. */
void BootSequence_Advance(struct DbaaBootSequenceData *data) {
  if (++data->timer >= data->duration) {
    data->screen++;
    if (data->screen > 3) {
      data->flags |= 0x80000000;
      data->phase = 0;
    } else {
      data->flags &= ~1;
      BootSequence_ClearScreen(data->screen);
      BootSequence_LoadScreen(data->screen);
      gBlendShadow[0] = 0xFF;
      gBlendShadow[1] = 0;
      gBlendShadow[2] = 16;
      data->timer = 0;
      data->duration = data->script[data->screen].fadeInFrames;
      data->phase = BootSequence_FadeIn;
    }
  }
}
