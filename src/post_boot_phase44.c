#include "post_boot.h"
/* USA 0x080F0390: 40 complete bytes match the ROM. */
void PostBoot_Phase44(struct DbaaPostBootData *data) {
  gDisplayControlShadow = 0x1040;
  gBlendShadow[0] = 0;
  gBlendShadow[1] = 0;
  gBlendShadow[2] = 0;
  data->phase = PostBoot_Phase45;
}
