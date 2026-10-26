#include "post_boot.h"
/* USA 0x080EE810: 220 complete bytes match the ROM. */
void PostBoot_Update(void) {
  struct DbaaPostBootData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaPostBootData);
  data->elapsed++;
  gDbaaGameState.word14++;
  if (data->flags & 0x20) {
    data->flags = (data->flags & ~0x20) | 0x40;
  } else if (data->flags & 0x40) {
    data->flags &= ~0x40;
    data->flags &= ~0x10;
  }
  if ((gPressedKeys & 0xB) && !(data->flags & 4)) {
    data->skipTask = PostBoot_CreateSkipTask(data);
    data->flags |= 1;
    data->flags |= 4;
  }
  if (data->phase)
    data->phase(data);
  if (data->flags & 0x40000000)
    gCurrentTask->callback = PostBoot_Finish;
  gDisplayControlShadow &= 0xF7FF;
}
