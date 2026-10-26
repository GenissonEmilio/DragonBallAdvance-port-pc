#include "post_boot.h"
/* USA 0x080F020C: 24 complete bytes match the ROM. */
void PostBoot_Phase29(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(10);
  data->phase = PostBoot_Phase30;
}
