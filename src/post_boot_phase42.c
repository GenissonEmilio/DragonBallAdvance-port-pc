#include "post_boot.h"
/* USA 0x080F032C: 60 complete bytes match the ROM. */
void PostBoot_Phase42(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow &= 0xF0FF;
    data->phase = PostBoot_Phase43;
  }
}
