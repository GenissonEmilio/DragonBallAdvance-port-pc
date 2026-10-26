#include "runtime.h"
#include "tasks.h"

/* USA 0x0810D94C: walk IWRAM task links and invoke eligible callbacks. */
void Tasks_RunFrame(void)
{
    gCurrentTask = gTaskHeads[0];
    if ((gSystemFlags & 0x800) == 0)
    {
        while (gCurrentTask != (struct DbaaTask *)0x03000000)
        {
            gNextTask = (struct DbaaTask *)(0x03000000 + gCurrentTask->nextOffset);
            if ((gCurrentTask->flags & 1) == 0)
                gCurrentTask->callback();
            gCurrentTask = gNextTask;
            if (gFrameBeginByte != 0)
            {
                Func_0810ADAC();
                gFrameBeginByte = 0;
            }
        }
    }
    else
    {
        while (gCurrentTask != (struct DbaaTask *)0x03000000)
        {
            gNextTask = (struct DbaaTask *)(0x03000000 + gCurrentTask->nextOffset);
            if ((gCurrentTask->flags & 5) == 4)
                gCurrentTask->callback();
            gCurrentTask = gNextTask;
            if (gFrameBeginByte != 0)
            {
                Func_0810ADAC();
                gFrameBeginByte = 0;
            }
        }
    }
    gCurrentTask = 0;
    gNextTask = 0;
}
