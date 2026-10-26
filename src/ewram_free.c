/* USA 0x8115690: Release an EWRAM block and merge physically adjacent free
 * nodes; ignore failure sentinel. */
#include "task_memory.h"

void Heap_EwramFree(void *data) {
  struct DbaaEwramNode *node = data, *scan, *fast, *slow;
  if (data == 0 || gEwramAllocationFailure == data)
    return;
  node = (struct DbaaEwramNode *)((DbaaU8 *)node - 8);
  slow = &gEwramTaskHeap;
  scan = slow;
  if (node != slow) {
    do {
      slow = scan;
      scan = slow->next;
    } while (node != scan);
  }
  if (node->state < 0)
    node->state = -node->state;
  if ((struct DbaaEwramNode *)((DbaaU8 *)slow + slow->state) == node) {
    if (slow->state > 0) {
      slow->next = scan->next;
      slow->state += node->state;
      node = slow;
    }
  }
  fast = (struct DbaaEwramNode *)((DbaaU8 *)node + node->state);
  if (fast == node->next) {
    if (fast->state > 0) {
      node->state += fast->state;
      node->next = fast->next;
    }
  }
}
