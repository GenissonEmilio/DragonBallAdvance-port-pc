#include "post_boot.h"
/* USA 0x080F0418: 28 complete bytes match the ROM. */
void PostBoot_Phase48(struct DbaaPostBootData *data) {
  if (!(data->flags & 0x10)) {
    data->flags |= 0x40000000;
    data->phase = 0;
  }
}
