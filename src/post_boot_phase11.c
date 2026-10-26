#include "post_boot.h"
/* USA 0x080EFE30: 72 complete bytes match the ROM. */
void PostBoot_Phase11(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow &= ~(1 << (data->backgrounds[5].background + 8));
    data->phase = PostBoot_Phase12;
  }
}
