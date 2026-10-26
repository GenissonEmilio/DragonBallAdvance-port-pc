#include "post_boot.h"
/* USA 0x080EFDB0: 32 complete bytes match the ROM. */
void PostBoot_Phase8(struct DbaaPostBootData *data) {
  PostBoot_ClearBackgroundMap(data->backgrounds[0].background);
  data->phase = PostBoot_Phase9;
}
