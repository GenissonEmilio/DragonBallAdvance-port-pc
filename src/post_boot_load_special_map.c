#include "post_boot.h"
/* USA 0x080EF344: 112 complete bytes match the ROM. */
void PostBoot_LoadSpecialMap(DbaaU8 screenBase, DbaaU8 palette) {
  DbaaU16 *destination = (DbaaU16 *)(0x06000000 + screenBase * 0x800);
  DbaaU16 paletteBits = (palette & 15) << 12;
  DbaaU8 row, col;
  for (row = 0; row <= 9; row++) {
    DbaaU16 value = gPostBootMapRows[row] | paletteBits;
    for (col = 0; col < 32; col++)
      *destination++ = value;
  }
  for (row = 0; row <= 9; row++) {
    DbaaU16 value = gPostBootMapRows[9 - row] | paletteBits | 0x800;
    for (col = 0; col < 32; col++)
      *destination++ = value;
  }
}
