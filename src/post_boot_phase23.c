#include "post_boot.h"
/* USA 0x080F00E8: 36 complete bytes match the ROM. */
void PostBoot_Phase23(struct DbaaPostBootData *data) {
  DbaaU32 flags = data->flags;
  if (!(flags & 0x10)) {
    /* Preserve the separate wait and skip tests. */
    __asm__("" : "+r"(flags));
    if (!(flags & 1))
      data->phase = PostBoot_Phase24;
  }
}
