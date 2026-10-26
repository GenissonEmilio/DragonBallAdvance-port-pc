/* USA 0x810da88: Release an IWRAM block and merge physically adjacent free
 * predecessors/successors. */
#include "task_memory.h"

void Tasks_IwramFree(void *data) {
  struct DbaaIwramNode *node = data, *fast;
  register struct DbaaIwramNode *slow __asm__("r1");
  node = (struct DbaaIwramNode *)((DbaaU8 *)node - 4);
  slow = &gIwramTaskHeap;
  fast = slow;
  if (node != slow) {
    do {
      slow = fast;
      fast = TASK_IWRAM_POINTER(slow->next);
    } while (node != fast);
  }
  if (node->state < 0)
    node->state = -node->state;
  if ((struct DbaaIwramNode *)((DbaaU8 *)slow + slow->state) == node) {
    DbaaU16 state = slow->state;
    if (slow->state > 0) {
      slow->next = fast->next;
      slow->state = state + node->state;
      node = slow;
    }
  }
  fast = (struct DbaaIwramNode *)((DbaaU8 *)node + node->state);
  if (fast == TASK_IWRAM_POINTER(node->next)) {
    if (fast->state > 0) {
      node->state += fast->state;
      node->next = fast->next;
    }
  }
}
