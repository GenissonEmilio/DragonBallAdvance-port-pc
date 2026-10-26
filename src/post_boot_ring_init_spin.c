#include "post_boot.h"
/* USA 0x080F0768: 68 complete bytes match the ROM. */
int PostBoot_RingInitSpin(struct DbaaPostBootRingData *data) {
  data->angularVelocity = 0;
  data->angularAcceleration = 0xC000;
  data->radialVelocity =
      (int)0xFFE20000 / (int)(gPostBootTimeline[data->step] - data->elapsed);
  data->radialAcceleration = 0;
  data->phase = PostBoot_RingSpin;
  PostBoot_RingDraw(data);
  return 0;
}
