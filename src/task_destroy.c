/* USA 0x810d894: Unlink a task, invoke its destructor with the task pointer,
 * and return descriptor/data storage. */
#include "task_memory.h"

void Task_Destroy(struct DbaaTask *task) {
  struct DbaaTask *next, *prev;
  if (!(task->flags & 2)) {
    prev = TASK_IWRAM_POINTER(task->unknown02);
    next = TASK_IWRAM_POINTER(task->nextOffset);
    if (prev != (void *)0x03000000 && next != (void *)0x03000000) {
      if (task->onDestroy != 0)
        task->onDestroy(task);
      if (task == gNextTask)
        gNextTask = TASK_IWRAM_POINTER(task->nextOffset);
      if (task == gNextTaskForDestruction)
        gNextTaskForDestruction = TASK_IWRAM_POINTER(task->nextOffset);
      prev = TASK_IWRAM_POINTER(task->unknown02);
      next = TASK_IWRAM_POINTER(task->nextOffset);
      prev->nextOffset = (DbaaU16)next;
      next->unknown02 = (DbaaU16)prev;
      if (task->dataOffset != 0) {
        if (task->flags & 0x10)
          Heap_EwramFree((void *)(0x02000000 + task->dataOffset * 4));
        else
          Tasks_IwramFree(TASK_IWRAM_POINTER(task->dataOffset));
      }
      gTaskHeads[--gFreeTaskIndex] = task;
      task->unknown00 = 0;
      task->unknown02 = 0;
      task->callback = Task_UnusedSentinel;
      task->priority = 0;
      task->flags = 0;
      task->dataOffset = 0;
    }
  }
}
