#include "post_boot.h"
/* USA 0x080F01B0: 36 complete bytes match the ROM. */
void PostBoot_Phase27(struct DbaaPostBootData *data) {

  PostBoot_ClearBackgroundMap(data->backgrounds[9].background);
  data->phase = PostBoot_Phase28;
}
