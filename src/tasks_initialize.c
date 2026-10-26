#include "tasks.h"
#include "hardware.h"

extern struct DbaaTask gTasks[];
extern int gFreeTaskIndex;
extern struct DbaaTask *gNextTaskForDestruction;
extern struct DbaaTask gEmptyTask;
extern DbaaU32 gTaskHeapLimit;
extern DbaaU16 gTaskHeapFreeHeader[];
struct DbaaTask *Tasks_AllocateSlot(void);
void Task_HeadSentinel(void);
void Task_TailSentinel(void);

int Tasks_Initialize(void)
{
    struct DbaaTask *task;
    int i;

    gCurrentTask = 0;
    gNextTask = 0;
    gFreeTaskIndex = 0;
    gNextTaskForDestruction = 0;
    DMA_FILL32(0, gTasks, 0x85000080);
    for (i = 0; i < 128; i++)
        gTaskHeads[i] = &gTasks[i];
    task = Tasks_AllocateSlot();
    if (task == 0)
        return 0;
    task->callback = Task_HeadSentinel;
    task->priority = 0;
    task->flags = 0;
    task->unknown00 = 0;
    task->unknown02 = 0;
    task->nextOffset = (DbaaU16)Tasks_AllocateSlot();
    if ((struct DbaaTask *)(0x03000000 + task->nextOffset) == (struct DbaaTask *)0x03000000)
        return 0;
    ((struct DbaaTask *)(0x03000000 + task->nextOffset))->unknown02 = (DbaaU16)task;
    task = (struct DbaaTask *)(0x03000000 + task->nextOffset);
    task->callback = Task_TailSentinel;
    task->priority = 0xFFFF;
    task->flags = 0;
    task->unknown00 = 0;
    task->nextOffset = 0;
    gEmptyTask.unknown00 = 0;
    gEmptyTask.unknown02 = 0;
    gEmptyTask.nextOffset = 0;
    gEmptyTask.dataOffset = gTaskHeapLimit;
    gTaskHeapFreeHeader[0] = 0;
    gTaskHeapFreeHeader[1] = 0x2604;
    return 1;
}
