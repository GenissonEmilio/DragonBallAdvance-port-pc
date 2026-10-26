#include "post_boot.h"
/* USA 0x080EFF20: 64 complete bytes match the ROM. */
void PostBoot_Phase15(struct DbaaPostBootData *data) {
  DbaaU16 zero;
  DbaaU16 *source;
  gDisplayControlShadow &= 0xDFFF;
  source = &zero;
  /* Preserve the scratch address before its zero store. */
  __asm__("" : : "r"(source));
  *source = 0;
  Bios_CpuSet(source, gWindowShadow, 0x01000006);
  data->phase = PostBoot_Phase16;
}
