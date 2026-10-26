#include "post_boot.h"
/* USA 0x080F027C: 88 complete bytes match the ROM. */
void PostBoot_Phase36(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow &= ~(1 << (data->backgrounds[11].background + 8));
    gDisplayControlShadow &= ~(1 << (data->backgrounds[12].background + 8));
    data->phase = PostBoot_Phase37;
  }
}
