#include "post_boot.h"
/* USA 0x080F0830: 24 complete bytes match the ROM. */
int PostBoot_RingTail(struct DbaaPostBootRingData *data) {
  PostBoot_RingStep(data);
  PostBoot_RingDraw(data);
  return 0;
}
