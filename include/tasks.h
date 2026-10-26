#ifndef DBAA_TASKS_H
#define DBAA_TASKS_H

#include "game_state.h"

typedef void (*DbaaTaskCallback)(void);
struct DbaaTask;
typedef void (*DbaaTaskDestructor)(struct DbaaTask *task);

struct DbaaTask
{
    DbaaU16 unknown00; /* Parent task's IWRAM offset. */
    DbaaU16 unknown02; /* Previous task's IWRAM offset. */
    DbaaU16 nextOffset;
    DbaaU16 dataOffset;
    DbaaTaskCallback callback;
    DbaaTaskDestructor onDestroy;
    DbaaU16 priority;
    DbaaU16 flags;
};

struct DbaaCounterTaskData
{
    DbaaU8 byte00;
    DbaaU8 unknown01;
    DbaaU16 half02;
};

struct DbaaTask *Task_Create(DbaaTaskCallback callback, DbaaU16 size,
                            DbaaU16 priority, DbaaU16 flags, DbaaTaskDestructor onDestroy);
extern struct DbaaTask *gCounterTask;
extern struct DbaaTask *gTaskHeads[];
extern struct DbaaTask *gCurrentTask;
extern struct DbaaTask *gNextTask;

#endif
