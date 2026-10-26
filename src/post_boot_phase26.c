#include "post_boot.h"
/* USA 0x080F0184: 44 complete bytes match the ROM. */
void PostBoot_Phase26(struct DbaaPostBootData *data) {
  if (!(data->flags & 1)) {
    PostBoot_ClearBackgroundMap(data->backgrounds[8].background);
    data->phase = PostBoot_Phase27;
  }
}
