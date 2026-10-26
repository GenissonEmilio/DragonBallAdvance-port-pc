#include "post_boot.h"
/* USA 0x080EFFD8: 36 complete bytes match the ROM. */
void PostBoot_Phase18(struct DbaaPostBootData *data) {
  DbaaU32 flags = data->flags;
  if (!(flags & 0x10)) {
    /* Keep the separate wait and skip tests from the original control flow. */
    __asm__("" : "+r"(flags));
    if (!(flags & 1))
      data->phase = PostBoot_Phase19;
  }
}
