#include "post_boot.h"
/* USA 0x080F02D4: 24 complete bytes match the ROM. */
void PostBoot_Phase37(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(13);
  data->phase = PostBoot_Phase38;
}
