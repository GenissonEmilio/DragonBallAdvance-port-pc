#include "sequences.h"
/* USA 0x0800C230: 108 complete bytes match the ROM. */
void ScreenFade_Commit(void) {
  struct DbaaTask *task = gScreenFadeTask;
  if (task != 0) {
    struct DbaaFadeData *data = RESOLVED_TASK_DATA(task, struct DbaaFadeData);
    if (data->flags & 1)
      gBlendShadow[0] = 0x80;
    else
      gBlendShadow[0] = 0xC0;
    gBlendShadow[0] |= data->bgMask & 0x3F;
    gBlendShadow[2] = (data->value >> 8) & 0x1F;
  }
}
