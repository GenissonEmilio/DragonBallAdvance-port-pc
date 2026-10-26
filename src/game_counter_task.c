#include "runtime.h"
#include "tasks.h"

/* USA 0x08001468: attach the increment/reset callbacks and initialize their data. */
void Game_CreateCounterTask(void)
{
    struct DbaaTask *task;
    struct DbaaCounterTaskData *data;

    task = Task_Create(State_IncrementWord10IfFlag22, 4, 0x100, 0,
                       (DbaaTaskDestructor)Game_ResetVideoStateCallback);
    if (task->flags & 0x10)
        data = (struct DbaaCounterTaskData *)(0x02000000 + task->dataOffset * 4);
    else
        data = (struct DbaaCounterTaskData *)(0x03000000 + task->dataOffset);

    data->byte00 = 0;
    data->half02 = 0;
    gCounterTask = task;
    gDbaaGameState.word14 = 0;
    Func_080C863C(0, 0, 4, 0);
}
