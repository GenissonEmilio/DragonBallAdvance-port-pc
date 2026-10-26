#include "post_boot.h"
/* USA 0x080F07AC: 56 complete bytes match the ROM. */
int PostBoot_RingSpin(struct DbaaPostBootRingData *data) {
  PostBoot_RingStep(data);
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    data->phase = PostBoot_RingRelease;
  }
  PostBoot_RingDraw(data);
  return 0;
}
