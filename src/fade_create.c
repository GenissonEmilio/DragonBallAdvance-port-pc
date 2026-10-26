#include "sequences.h"
/* USA 0x0800C0C8: 264 complete bytes match the ROM. */
struct DbaaFadeData *Func_0800C0C8(int argument) {
  struct DbaaTask *task;
  struct DbaaFadeData *data;
  DbaaU8 mode = argument;
  if (gScreenFadeTask != 0)
    Task_Destroy(gScreenFadeTask);
  task = Task_Create(ScreenFade_Run, 12, 0xFFFE, 4, ScreenFade_OnDestroy);
  gScreenFadeTask = task;
  data = RESOLVED_TASK_DATA(task, struct DbaaFadeData);
  data->step = 0;
  data->value = 0;
  data->bgMask = 0x3F;
  data->flags = 0;
  data->target = 0;
  data->delay = 0;
  switch (mode) {
  case 3:
  case 7:
    data->flags |= 1;
  case 1:
  case 5:
    data->flags |= 2;
    data->step = 0x400;
    if (mode > 4)
      data->target = 0x800;
    else
      data->target = 0x1000;
    break;
  case 4:
  case 8:
    data->flags |= 1;
  case 2:
  case 6:
    data->step = -0x200;
    data->target = 0;
    if (mode > 4)
      data->value = 0x800;
    else
      data->value = 0x1000;
    break;
  }
  if (mode == 2 || mode == 4)
    data->delay = 6;
  ScreenFade_Commit();
  return data;
}
