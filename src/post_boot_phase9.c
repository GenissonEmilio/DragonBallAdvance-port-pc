#include "post_boot.h"
/* USA 0x080EFDD0: 24 complete bytes match the ROM. */
void PostBoot_Phase9(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(5);
  data->phase = PostBoot_Phase10;
}
