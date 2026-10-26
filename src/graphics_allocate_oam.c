/* USA 0x081119F0: 152 complete bytes match the ROM. */
#include "sprites.h"
struct DbaaOamEntry *Graphics_AllocateOam(DbaaU8 order) {
  if (order > 31)
    order = 31;
  if ((DbaaS8)gOamFreeIndex < 0)
    return gTaskHeapLimit;
  if ((DbaaU8)gOamOrderHeads[order] == 0xFF) {
    gOamAllocatedEntries[gOamFreeIndex].next = -1;
    gOamOrderHeads[order] = gOamFreeIndex;
    gOamOrderTails[order] = gOamFreeIndex;
  } else {
    gOamAllocatedEntries[gOamFreeIndex].next = -1;
    gOamAllocatedEntries[(DbaaU8)gOamOrderTails[order]].next = gOamFreeIndex;
    gOamOrderTails[order] = gOamFreeIndex;
  }
  gOamFreeIndex++;
  return &gOamAllocatedEntries[gOamFreeIndex - 1];
}
