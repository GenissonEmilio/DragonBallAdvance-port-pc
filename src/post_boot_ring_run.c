#include "post_boot.h"
/* USA 0x080F0664: 76 complete bytes match the ROM. */
void PostBoot_RingRun(void) {
  struct DbaaPostBootRingData *data =
      (struct DbaaPostBootRingData *)SEQUENCE_DATA(gCurrentTask);
  data->elapsed = data->parent->elapsed;
  data->step = data->parent->step;
  if (data->phase(data) == 0)
    data->parent->step = data->step;
}
