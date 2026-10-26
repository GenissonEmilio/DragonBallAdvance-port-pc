#include "post_boot.h"
/* USA 0x080EFF60: 24 complete bytes match the ROM. */
void PostBoot_Phase16(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(7);
  data->phase = PostBoot_Phase17;
}
