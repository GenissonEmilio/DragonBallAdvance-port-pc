#include "post_boot.h"
/* USA 0x080F0304: 40 complete bytes match the ROM. */
void PostBoot_Phase40(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    data->phase = PostBoot_Phase41;
  }
}
