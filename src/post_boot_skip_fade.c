#include "post_boot.h"
/* USA 0x080EFA30: 116 complete bytes match the ROM. */
void PostBoot_SkipFade(void) {
  struct DbaaPostBootSkipData *data =
      (struct DbaaPostBootSkipData *)SEQUENCE_DATA(gCurrentTask);
  data->elapsed++;
  gBlendShadow[2] = (data->elapsed << 4) / data->duration;
  if (data->elapsed >= data->duration) {
    struct DbaaPostBootData *parent = data->parent;
    gBlendShadow[2] = 16;
    parent->flags |= 0x40000000;
    parent->skipTask = 0;
    Task_Destroy(gCurrentTask);
  }
}
