#include "post_boot.h"
/* USA 0x080EF29C: 168 complete bytes match the ROM. */
void PostBoot_LoadSpecialTiles(DbaaU8 charBase) {
  /* Empty constraints preserve the bound, offset and expanded-word registers.
   */
  register DbaaU32 limit __asm__("r8") = 9;
  DbaaU32 *destination = ({
    __asm__("" : "+h"(limit));
    (DbaaU32 *)(0x06000000 + charBase * 0x4000);
  });
  DbaaU8 i;
  i = 0;
  do {
    DbaaU32 value = ({
      DbaaU32 offset = i * 4;
      __asm__("" : : "r"(offset) : "r1");
      gPostBootTileRuns[i][0];
    });
    register DbaaU32 word __asm__("r3") = ({
      DbaaU32 expanded = (value << 4) | value | (value << 8) | (value << 12) |
                         (value << 16) | (value << 20) | (value << 24);
      /* Sequence the final unsigned shift after all earlier reads. */
      value <<= 28;
      expanded | value;
    });
    DbaaU8 count = ({
      __asm__("" : : "r"(word));
      gPostBootTileRuns[i][1];
    });
    DbaaU8 j;
    for (j = 0; j < count; j++)
      *destination++ = word;
    value = gPostBootTileRuns[i][2];
    word = ({
      DbaaU32 expanded = (value << 4) | value | (value << 8) | (value << 12) |
                         (value << 16) | (value << 20) | (value << 24);
      /* Sequence the final unsigned shift after all earlier reads. */
      value <<= 28;
      expanded | value;
    });
    __asm__("" : : "r"(word));
    count = gPostBootTileRuns[i][3];
    for (j = 0; j < count; j++)
      *destination++ = word;
  } while (++i < limit);
}
