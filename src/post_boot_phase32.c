#include "post_boot.h"
/* USA 0x080F0224: 24 complete bytes match the ROM. */
void PostBoot_Phase32(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(11);
  data->phase = PostBoot_Phase33;
}
