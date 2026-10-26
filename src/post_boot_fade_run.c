#include "post_boot.h"
/* USA 0x080EF4F0: 120 complete bytes match the ROM. */
void PostBoot_FadeRun(void) {
  struct DbaaPostBootFadeData *data =
      (struct DbaaPostBootFadeData *)SEQUENCE_DATA(gCurrentTask);
  data->current += data->increment;
  gBlendShadow[2] = data->current >> 8;
  data->elapsed++;
  if (data->elapsed >= data->duration) {
    gBlendShadow[2] = data->target;
    data->parent->flags |= 0x20;
    data->parent->fade = 0;
    Task_Destroy(gCurrentTask);
  }
}
