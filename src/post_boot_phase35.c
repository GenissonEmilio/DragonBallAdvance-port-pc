#include "post_boot.h"
/* USA 0x080F0254: 40 complete bytes match the ROM. */
void PostBoot_Phase35(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    data->phase = PostBoot_Phase36;
  }
}
