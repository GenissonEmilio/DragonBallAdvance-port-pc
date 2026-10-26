#include "post_boot.h"
/* USA 0x080F06B0: 12 complete bytes match the ROM. */
int PostBoot_RingBegin(struct DbaaPostBootRingData *data) {
  data->phase = PostBoot_RingInitContract;
  return 0;
}
