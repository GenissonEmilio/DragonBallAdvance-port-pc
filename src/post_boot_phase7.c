#include "post_boot.h"
/* USA 0x080EFD50: 96 complete bytes match the ROM. */
void PostBoot_Phase7(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow &= ~((1 << (data->backgrounds[0].background + 8)) |
                               (1 << (data->backgrounds[3].background + 8)) |
                               (1 << (data->backgrounds[4].background + 8)));
    data->phase = PostBoot_Phase8;
  }
}
