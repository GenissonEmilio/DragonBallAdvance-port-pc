/* USA 0x810da20: First-fit IWRAM allocation: 16-bit offsets, signed block
 * states, four-byte node header. */
#include "task_memory.h"

void *Tasks_IwramAlloc(DbaaU16 requested) {
  struct DbaaIwramNode *cur, *next;
  DbaaU16 size = requested;
  size = (size + 3) / 4;
  if (size == 0)
    return 0;
  size = size * 4 + 4;
  cur = &gIwramTaskHeap;
  while (1) {
    DbaaS16 signedSize = size;
    if (signedSize <= cur->state) {
      if (signedSize != cur->state) {
        DbaaS16 offset = size + 4;
        if (offset > cur->state) {
          if (TASK_IWRAM_POINTER(cur->next) == (void *)0x03000000)
            return 0;
          cur = TASK_IWRAM_POINTER(cur->next);
          continue;
        }
        next = (struct DbaaIwramNode *)((DbaaU8 *)cur + size);
        next->next = cur->next;
        next->state = cur->state - size;
        cur->next = (DbaaU16)next;
      }
      cur->state = -size;
      return cur->space;
    }
    if (TASK_IWRAM_POINTER(cur->next) == (void *)0x03000000)
      return 0;
    cur = TASK_IWRAM_POINTER(cur->next);
  }
}
