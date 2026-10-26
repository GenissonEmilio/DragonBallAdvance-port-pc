#include "post_boot.h"
/* USA 0x080F0040: 56 complete bytes match the ROM. */
void PostBoot_Phase21(struct DbaaPostBootData *data) {
  if (data->flags & 0x40) {
    gDisplayControlShadow &= ~(1 << (data->backgrounds[7].background + 8));
    data->phase = PostBoot_Phase22;
  }
}
