#include "post_boot.h"
/* USA 0x080EFED8: 72 complete bytes match the ROM. */
void PostBoot_Phase14(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow &= ~(1 << (data->backgrounds[6].background + 8));
    data->phase = PostBoot_Phase15;
  }
}
