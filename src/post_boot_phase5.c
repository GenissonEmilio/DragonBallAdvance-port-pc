#include "post_boot.h"
/* USA 0x080EFCD8: 24 complete bytes match the ROM. */
void PostBoot_Phase5(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(4);
  data->phase = PostBoot_Phase6;
}
