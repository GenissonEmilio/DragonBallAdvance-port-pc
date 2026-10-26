#include "post_boot.h"
/* USA 0x080EFF78: 96 complete bytes match the ROM. */
void PostBoot_Phase17(struct DbaaPostBootData *data) {
  if (!(data->flags & 1)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      gDisplayControlShadow |= (1 << (data->backgrounds[7].background + 8));
      if (PostBoot_StartFade(data, 0))
        data->phase = PostBoot_Phase18;
    }
  }
}
