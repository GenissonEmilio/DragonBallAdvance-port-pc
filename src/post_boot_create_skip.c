#include "post_boot.h"
/* USA 0x080F0898: 116 complete bytes match the ROM. */
struct DbaaTask *PostBoot_CreateSkipTask(struct DbaaPostBootData *parent) {
  struct DbaaTask *task;
  struct DbaaPostBootSkipData *data;
  DbaaU16 zero;
  task = Task_Create(PostBoot_SkipRun, 16, 0x1000, 0, PostBoot_SkipOnDestroy);
  data = (struct DbaaPostBootSkipData *)SEQUENCE_DATA(task);
  {
    DbaaU16 *source = &zero;
    /* Keep the source address before storing zero. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, data, 0x01000008);
  }
  data->duration = 20;
  data->parent = parent;
  parent->skipTask = task;
  parent->flags |= 4;
  return task;
}
