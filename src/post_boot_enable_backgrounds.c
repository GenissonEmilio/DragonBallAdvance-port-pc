#include "post_boot.h"
/* USA 0x080EFB90: 80 complete bytes match the ROM. */
void PostBoot_EnableBackgrounds(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow |= (1 << (data->backgrounds[0].background + 8)) |
                             (1 << (data->backgrounds[1].background + 8));
    data->phase = PostBoot_DisableBackgrounds;
  }
}
