#include "post_boot.h"
/* USA 0x08113C60: 48 complete bytes match the ROM. */
void Vram_FreeTiles(void *vram) {
  if (gEwramAllocationFailure != vram) {
    DbaaU16 index = ((DbaaU32)vram - (DbaaU32)gGamePointer03002CB0) >> 7;
    gVramHeapMap[index] = 0;
  }
}
