#include "post_boot.h"
/* USA 0x080F01D4: 56 complete bytes match the ROM. */
void PostBoot_Phase28(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(9);
  gDisplayControlShadow |= 1 << (data->backgrounds[9].background + 8);
  data->phase = PostBoot_Phase29;
}
