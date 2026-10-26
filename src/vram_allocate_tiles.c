#include "post_boot.h"
/* USA 0x08113B80: 184 complete bytes match the ROM. */
void *Vram_AllocateTiles(DbaaU32 tiles) {
  register DbaaU32 blocks __asm__("r5") = ({
    register DbaaU32 value __asm__("r5") = tiles;
    DbaaU32 rounded = value + 3;
    /* Keep the input live through addition; this template is empty. */
    __asm__("" : : "r"(value));
    rounded >> 2;
  });
  DbaaU16 i, j;
  for (i = 0; i < (gGameHalf03002BEC >> 2); i++) {
    DbaaU16 size = gVramHeapMap[i];
    if (size == 0) {
      for (j = 0; j < blocks; j++) {
        if (i + j >= (gGameHalf03002BEC >> 2))
          return gEwramAllocationFailure;
        if (gVramHeapMap[i + j])
          break;
      }
      if (j == blocks) {
        gVramHeapMap[i] = blocks;
        return (DbaaU8 *)gGamePointer03002CB0 + i * 128;
      }
    } else {
      i += size - 1;
    }
  }
  return gEwramAllocationFailure;
}
