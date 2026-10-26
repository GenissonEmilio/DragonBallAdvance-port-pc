#include "post_boot.h"
/* USA 0x080F0078: 112 complete bytes match the ROM. */
void PostBoot_Phase22(struct DbaaPostBootData *data) {
  if (!(data->flags & 1)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      PostBoot_LoadMap(8);
      PostBoot_LoadPalette(8);
      PostBoot_ApplyBackground(8);
      gDisplayControlShadow |= 1 << (data->backgrounds[8].background + 8);
      if (PostBoot_StartFade(data, 0))
        data->phase = PostBoot_Phase23;
    }
  }
}
