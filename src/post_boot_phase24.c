#include "post_boot.h"
/* USA 0x080F010C: 64 complete bytes match the ROM. */
void PostBoot_Phase24(struct DbaaPostBootData *data) {
  if (!(data->flags & 1)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      if (PostBoot_StartFade(data, 1))
        data->phase = PostBoot_Phase25;
    }
  }
}
