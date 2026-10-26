#include "sequences.h"
/* USA 0x080F3464: 68 complete bytes match the ROM. */
void BootSequence_StartScreen(struct DbaaBootSequenceData *data) {
  BootSequence_ClearScreen(data->screen);
  BootSequence_LoadScreen(data->screen);
  gBlendShadow[0] = 0xFF;
  gBlendShadow[1] = 0;
  gBlendShadow[2] = 16;
  data->timer = 0;
  data->duration = data->script[data->screen].fadeInFrames;
  data->phase = BootSequence_FadeIn;
}
