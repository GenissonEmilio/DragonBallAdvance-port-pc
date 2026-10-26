#include "sequences.h"
/* USA 0x0800C38C: 24 complete bytes match the ROM. */
void ScreenFade_OnDestroy(struct DbaaTask *task) {
  gBlendShadow[0] = 0;
  gBlendShadow[2] = 0;
  gScreenFadeTask = 0;
}
