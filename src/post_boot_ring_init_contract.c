#include "post_boot.h"
/* USA 0x080F06BC: 68 complete bytes match the ROM. */
int PostBoot_RingInitContract(struct DbaaPostBootRingData *data) {
  data->angle = 0;
  data->angularVelocity = 0;
  data->angularAcceleration = 0;
  data->radius = 200 << 16;
  data->radialVelocity =
      (int)0xFF6E0000 / (int)(gPostBootTimeline[data->step] - data->elapsed);
  data->radialAcceleration = 0;
  data->phase = PostBoot_RingContract;
  return 0;
}
