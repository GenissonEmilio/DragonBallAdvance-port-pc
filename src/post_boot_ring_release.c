#include "post_boot.h"
/* USA 0x080F07E4: 76 complete bytes match the ROM. */
int PostBoot_RingRelease(struct DbaaPostBootRingData *data) {
  data->angularVelocity >>= 2;
  data->angularAcceleration = -0x6000;
  data->radialVelocity = 0xBBBBB;
  data->radialAcceleration = 0x6000;
  data->parent->flags &= ~0x1000;
  PostBoot_RingStep(data);
  data->phase = PostBoot_RingTail;
  PostBoot_RingDraw(data);
  return 0;
}
