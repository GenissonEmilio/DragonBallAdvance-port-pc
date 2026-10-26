/* USA 0x810d758: Create and insert a task in stable priority order, preserving
 * heap fallback and queue continuation. */
#include "task_memory.h"

struct DbaaTask *Task_Create(DbaaTaskCallback callback, DbaaU16 size,
                             DbaaU16 priority, DbaaU16 flags,
                             DbaaTaskDestructor onDestroy) {
  struct DbaaTask *slow, *task;
  DbaaU16 fast;
  /* This empty C scope preserves agbcc register allocation. */
  do
    ;
  while (0);
  task = 0;
  slow = 0;
  if (gFreeTaskIndex < 128) {
    struct DbaaTask *slot = gTaskHeads[gFreeTaskIndex++];
    task = slot;
  }
  if (task == 0)
    return &gEmptyTask;
  task->callback = callback;
  task->onDestroy = onDestroy;
  task->priority = priority;
  task->flags = flags;
  if (flags & 0x10) {
    if (size == 0)
      task->dataOffset = 0;
    else
      task->dataOffset = ((DbaaU32)Heap_EwramAlloc(size) - 0x02000000) >> 2;
    {
      void **failure = &gEwramAllocationFailure;
      void *data;
      /* Keep the failure-pointer address before selecting the data view. */
      __asm__("" : : "r"(failure));
      data = TASK_DATA_POINTER(task);
      if (*failure == data) {
        task->flags &= ~0x10;
        task->dataOffset = (DbaaU16)Tasks_IwramAlloc(size);
      }
    }
  } else {
    task->dataOffset = (DbaaU16)Tasks_IwramAlloc(size);
    if (size != 0 && task->dataOffset == 0) {
      task->flags |= 0x10;
      task->dataOffset = ((DbaaU32)Heap_EwramAlloc(size) - 0x02000000) >> 2;
    }
  }
  task->unknown00 = (DbaaU16)gCurrentTask;
  slow = gTaskHeads[0];
  fast = slow->nextOffset;
  while (TASK_IWRAM_POINTER(fast) != (void *)0x03000000) {
    struct DbaaTask *next = TASK_IWRAM_POINTER(fast);
    if (next->priority > priority) {
      next->unknown02 = (DbaaU16)task;
      task->nextOffset = slow->nextOffset;
      task->unknown02 = (DbaaU16)slow;
      slow->nextOffset = (DbaaU16)task;
      if ((DbaaU16)task == gNextTask->unknown02)
        gNextTask = task;
      break;
    }
    slow = next;
    fast = slow->nextOffset;
  }
  return task;
}
