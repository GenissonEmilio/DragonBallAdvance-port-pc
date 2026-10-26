#include "post_boot.h"
/* USA 0x080F0738: 48 complete bytes match the ROM. */
int PostBoot_RingHold(struct DbaaPostBootRingData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    data->phase = PostBoot_RingInitSpin;
  }
  PostBoot_RingDraw(data);
  return 0;
}
