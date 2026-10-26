/* USA 0x810dbf8: Destroy tasks in [lower, upper), preserving sentinel nodes and
 * recursive destructor continuation. */
#include "task_memory.h"

void Tasks_DestroyPriorityRange(DbaaU16 lower, DbaaU16 upper) {
  struct DbaaTask *cur = gTaskHeads[0];
  DbaaU16 offset = (DbaaU16)cur;
  /* Empty template: preserve the original continuation-pointer allocation. */
  __asm__("" ::: "r5");
  while (offset != 0) {
    if (cur->priority >= lower) {
      lower = 0;
      while (cur->priority < upper) {
        gNextTaskForDestruction = TASK_IWRAM_POINTER(cur->nextOffset);
        if (cur != gTaskHeads[0] && cur != gTaskHeads[1])
          Task_Destroy(cur);
        cur = gNextTaskForDestruction;
        if (cur == (void *)0x03000000)
          break;
        ++cur;
        --cur;
        gNextTaskForDestruction += 0;
      }
      gNextTaskForDestruction = (void *)(DbaaU32)lower;
      return;
    }
    offset = cur->nextOffset;
    cur = TASK_IWRAM_POINTER(offset);
  }
  gNextTaskForDestruction = 0;
}
