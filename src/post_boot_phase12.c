#include "post_boot.h"
/* USA 0x080EFE78: 24 complete bytes match the ROM. */
void PostBoot_Phase12(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(6);
  data->phase = PostBoot_Phase13;
}
