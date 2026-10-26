#include "post_boot.h"
/* USA 0x080F0368: 40 complete bytes match the ROM. */
void PostBoot_Phase43(struct DbaaPostBootData *data) {
  if (data->child0) {
    Task_Destroy(data->child0);
    data->child0 = 0;
  }
  data->phase = PostBoot_Phase44;
}
