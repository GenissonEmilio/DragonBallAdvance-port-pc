/* USA 0x811562c: First-fit EWRAM allocation with full pointers, signed block
 * states and an eight-byte header. */
#include "task_memory.h"

void *Heap_EwramAlloc(DbaaU32 requested) {
  struct DbaaEwramNode *cur, *next;
  DbaaU32 size = requested;
  size = (size + 3) / 4;
  if (size == 0)
    return gEwramAllocationFailure;
  size = size * 4 + 8;
  cur = &gEwramTaskHeap;
  while (1) {
    if (size <= cur->state) {
      if (size == cur->state) {
        cur->state = -size;
        return cur->space;
      } else {
        int offset = size + 8;
        if (offset > cur->state) {
          if (cur->next == 0)
            return gEwramAllocationFailure;
          cur = cur->next;
          continue;
        }
        next = (struct DbaaEwramNode *)((DbaaU8 *)cur + size);
        next->next = cur->next;
        /* The ROM reloads the state after writing the new node link. */
        next->state = *(volatile int *)&cur->state - size;
        cur->next = next;
        cur->state = -size;
        return cur->space;
      }
    }
    if (cur->next == 0)
      return gEwramAllocationFailure;
    cur = cur->next;
  }
}
