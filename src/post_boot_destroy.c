#include "post_boot.h"
/* USA 0x080EE654: 136 complete bytes match the ROM. */
void PostBoot_OnDestroy(struct DbaaTask *task) {
  struct DbaaPostBootData *data =
      (struct DbaaPostBootData *)SEQUENCE_DATA(task);
  gSystemFlags |= 0x01000000;
  if (data->child0)
    Task_Destroy(data->child0);
  if (data->scrollTasks[0])
    Task_Destroy(data->scrollTasks[0]);
  if (data->scrollTasks[1])
    Task_Destroy(data->scrollTasks[1]);
  if (data->child3)
    Task_Destroy(data->child3);
  if (data->skipTask)
    Task_Destroy(data->skipTask);
}
