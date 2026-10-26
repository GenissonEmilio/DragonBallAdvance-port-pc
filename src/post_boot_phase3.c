#include "post_boot.h"
/* USA 0x080EFC30: 88 complete bytes match the ROM. */
void PostBoot_Phase3(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow |= (1 << (data->backgrounds[0].background + 8)) |
                             (1 << (data->backgrounds[2].background + 8));
    PostBoot_LoadBackground(3);
    data->phase = PostBoot_Phase4;
  }
}
