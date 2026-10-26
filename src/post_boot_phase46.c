#include "post_boot.h"
/* USA 0x080F03FC: 28 complete bytes match the ROM. */
void PostBoot_Phase46(struct DbaaPostBootData *data) {
  if (!(data->flags & 0x1000))
    data->phase = PostBoot_Phase47;
}
