#include "post_boot.h"
/* USA 0x080F0700: 56 complete bytes match the ROM. */
int PostBoot_RingContract(struct DbaaPostBootRingData *data) {
  PostBoot_RingStep(data);
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    data->phase = PostBoot_RingHold;
  }
  PostBoot_RingDraw(data);
  return 0;
}
