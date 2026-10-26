#include "post_boot.h"
/* USA 0x080F02EC: 24 complete bytes match the ROM. */
void PostBoot_Phase38(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(14);
  data->phase = PostBoot_Phase39;
}
