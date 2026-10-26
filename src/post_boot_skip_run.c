#include "post_boot.h"
/* USA 0x080EF9BC: 116 complete bytes match the ROM. */
void PostBoot_SkipRun(void) {
  struct DbaaPostBootSkipData *data =
      (struct DbaaPostBootSkipData *)SEQUENCE_DATA(gCurrentTask);
  if (!(data->parent->flags & 0x10)) {
    gBlendShadow[0] = 0xBF;
    gBlendShadow[1] = 0;
    gBlendShadow[2] = 0;
    gWindowShadow[4] |= 0x20;
    gWindowShadow[5] |= 0x20;
    data->parent->flags |= 2;
    gCurrentTask->callback = PostBoot_SkipFade;
  }
}
