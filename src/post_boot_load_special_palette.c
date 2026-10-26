#include "post_boot.h"
/* USA 0x080F04E0: 108 complete bytes match the ROM. */
void PostBoot_LoadSpecialPalette(DbaaU8 palette) {
  DbaaU8 count = 8;
  DbaaU16 *destination = (DbaaU16 *)(gBgPaletteBuffer + palette * 32);
  DbaaU8 i;
  DbaaU16 zero;
  for (i = 0; i < count; i++)
    *destination++ = (gPostBootBlueLevels[i] << 10) & 0x7C00;
  {
    DbaaU16 *source = &zero;
    /* Keep the scratch address before writing the fill value. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, destination, ((16 - count) & 0x1FFFFF) | 0x01000000);
  }
  gSystemFlags |= 1;
}
