#include "post_boot.h"
/* USA 0x080F0848: 44 complete bytes match the ROM. */
void PostBoot_RingStep(struct DbaaPostBootRingData *data) {
  data->angularVelocity += data->angularAcceleration;
  data->angle += data->angularVelocity;
  data->radialVelocity += data->radialAcceleration;
  data->radius += data->radialVelocity;
  PostBoot_PositionRing(data, data->angle >> 16, data->radius >> 16);
}
