#include "post_boot.h"
/* USA 0x080EEBAC: 144 complete bytes match the ROM. */
void PostBoot_Phase34(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    DbaaU16 duration;
    data->step++;
    duration = gPostBootTimeline[data->step] - data->elapsed;
    data->scrollTasks[0] = PostBoot_CreateScroll(data, 11, 0, duration);
    data->scrollTasks[1] = PostBoot_CreateScroll(data, 12, 1, duration);
    gDisplayControlShadow |= 1 << (data->backgrounds[11].background + 8);
    gDisplayControlShadow |= 1 << (data->backgrounds[12].background + 8);
    data->phase = PostBoot_Phase35;
  }
}
