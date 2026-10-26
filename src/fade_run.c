#include "sequences.h"
/* USA 0x0800C29C: 200 complete bytes match the ROM. */
void ScreenFade_Run(void) {
  struct DbaaFadeData *data =
      RESOLVED_TASK_DATA(gCurrentTask, struct DbaaFadeData);
  gBlendShadow[0] = 0;
  gBlendShadow[2] = 0;
  if (data->flags & 0x10) {
    Task_Destroy(gCurrentTask);
    return;
  }
  /* The original caller also passes data in r0; the callee ignores it. */
  {
    register struct DbaaFadeData *argument __asm__("r0") = data;
    __asm__("" : : "r"(argument));
    ScreenFade_Commit();
  }
  if (!(data->flags & 2)) {
    if (data->step < 0) {
      if (data->value <= data->target)
        data->flags |= 0x10;
    } else if (data->value >= data->target)
      data->flags |= 0x10;
  }
  if (data->delay == 0) {
    data->value += data->step;
    if (data->step < 0) {
      if (data->value < data->target)
        data->value = 0;
    } else if (data->value > data->target)
      data->value = data->target;
  } else
    data->delay--;
}
