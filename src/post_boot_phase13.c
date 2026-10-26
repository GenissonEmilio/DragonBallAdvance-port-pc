#include "post_boot.h"
/* USA 0x080EFE90: 72 complete bytes match the ROM. */
void PostBoot_Phase13(struct DbaaPostBootData *data) {
  if (data->elapsed >= gPostBootTimeline[data->step]) {
    data->step++;
    gDisplayControlShadow |= (1 << (data->backgrounds[6].background + 8));
    data->phase = PostBoot_Phase14;
  }
}
