#include "post_boot.h"
/* USA 0x080F03B8: 68 complete bytes match the ROM. */
void PostBoot_Phase45(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    data->child3 = PostBoot_CreateRing(data);
    data->flags |= 0x1000;
    data->phase = PostBoot_Phase46;
  }
}
