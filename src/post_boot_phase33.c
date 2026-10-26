#include "post_boot.h"
/* USA 0x080F023C: 24 complete bytes match the ROM. */
void PostBoot_Phase33(struct DbaaPostBootData *data) {
  PostBoot_LoadBackground(12);
  data->phase = PostBoot_Phase34;
}
