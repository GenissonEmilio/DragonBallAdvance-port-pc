#include "post_boot.h"
/* USA 0x080EEC3C: 144 complete bytes match the ROM. */
void PostBoot_Phase39(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    DbaaU16 duration;
    data->step++;
    duration = gPostBootTimeline[data->step] - data->elapsed;
    data->scrollTasks[0] = PostBoot_CreateScroll(data, 13, 0, duration);
    data->scrollTasks[1] = PostBoot_CreateScroll(data, 14, 1, duration);
    gDisplayControlShadow |= 1 << (data->backgrounds[13].background + 8);
    gDisplayControlShadow |= 1 << (data->backgrounds[14].background + 8);
    data->phase = PostBoot_Phase40;
  }
}
