#include "post_boot.h"
/* USA 0x080F0584: 68 complete bytes match the ROM. */
void PostBoot_CurtainWait(void) {
  struct DbaaPostBootCurtainData *data =
      (struct DbaaPostBootCurtainData *)SEQUENCE_DATA(gCurrentTask);
  if (data->parent->elapsed > 259)
    gCurrentTask->callback = PostBoot_CurtainMove;
}
