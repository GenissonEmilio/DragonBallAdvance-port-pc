#ifndef DBAA_TASK_MEMORY_H
#define DBAA_TASK_MEMORY_H

#include "tasks.h"

struct DbaaIwramNode {
  DbaaU16 next;
  DbaaS16 state;
  DbaaU8 space[0];
};

struct DbaaEwramNode {
  struct DbaaEwramNode *next;
  int state;
  DbaaU8 space[0];
};

extern struct DbaaIwramNode gIwramTaskHeap;
extern struct DbaaEwramNode gEwramTaskHeap;
extern void *gEwramAllocationFailure;
extern struct DbaaTask gEmptyTask;
extern int gFreeTaskIndex;
extern struct DbaaTask *gNextTaskForDestruction;

void *Tasks_IwramAlloc(DbaaU16 size);
void Tasks_IwramFree(void *data);
void *Heap_EwramAlloc(DbaaU32 size);
void Heap_EwramFree(void *data);
void Task_Destroy(struct DbaaTask *task);
void Tasks_DestroyPriorityRange(DbaaU16 lower, DbaaU16 upper);
void Task_HeadSentinel(void);
void Task_TailSentinel(void);
void Task_UnusedSentinel(void);

#define TASK_IWRAM_POINTER(offset) ((void *)(0x03000000 + (DbaaU32)(offset)))
#define TASK_DATA_POINTER(task)                                                \
  (((task)->flags & 0x10) ? (void *)(0x02000000 + (task)->dataOffset * 4)      \
                          : TASK_IWRAM_POINTER((task)->dataOffset))

#endif
