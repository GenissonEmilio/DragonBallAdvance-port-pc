#include "post_boot.h"
/* USA 0x080F04A8: 56 complete bytes match the ROM. */
void PostBoot_ClearBackgroundMap(DbaaU8 background) {
  DbaaU16 mapBase = (gBgControlShadow[background] >> 8) & 31;
  DbaaU16 zero;
  DbaaU16 *source = &zero;
  /* Preserve the scratch address before its zero store. */
  __asm__("" : : "r"(source));
  *source = 0;
  Bios_CpuSet(source, (void *)(0x06000000 + mapBase * 0x800), 0x01000800);
}
