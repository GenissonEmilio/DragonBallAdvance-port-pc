#include "post_boot.h"
/* USA 0x080F05CC: 148 complete bytes match the ROM. */
struct DbaaTask *PostBoot_CreateRing(struct DbaaPostBootData *parent) {
  struct DbaaTask *task;
  struct DbaaPostBootRingData *data;
  DbaaU16 zero;
  gDisplayControlShadow |= 0x1000;
  task = Task_Create(PostBoot_RingRun, 52, 0x400, 0, PostBoot_RingOnDestroy);
  data = (struct DbaaPostBootRingData *)SEQUENCE_DATA(task);
  {
    DbaaU16 *source = &zero;
    /* Keep the scratch address before its zero store. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, data, 0x0100001A);
  }
  data->sprites = &parent->sprites[2];
  data->elapsed = parent->elapsed;
  data->step = parent->step;
  data->parent = parent;
  parent->child3 = task;
  data->phase = PostBoot_RingBegin;
  return task;
}
