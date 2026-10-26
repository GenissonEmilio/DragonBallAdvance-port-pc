#include "backgrounds.h"
#include "post_boot.h"
/* USA 0x080EF7AC: 268 complete bytes match the ROM. */
struct DbaaTask *PostBoot_CreateScroll(struct DbaaPostBootData *parent,
                                       DbaaU8 index, DbaaU8 slot,
                                       DbaaU16 duration) {
  struct DbaaTask *task;
  struct DbaaPostBootScrollData *data;
  DbaaU16 zero;
  int delta;
  DbaaU32 initialFixed;
  task =
      Task_Create(PostBoot_ScrollRun, 32, 0x400, 0, PostBoot_ScrollOnDestroy);
  data = (struct DbaaPostBootScrollData *)SEQUENCE_DATA(task);
  {
    DbaaU16 *source = &zero;
    /* Preserve the scratch address before its zero store. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, data, 0x01000010);
  }
  data->duration = duration;
  data->index = index;
  data->slot = slot;
  data->entry = &parent->backgrounds[index];
  data->background = data->entry->background;
  data->parent = parent;
  parent->scrollTasks[slot] = task;
  parent->flags |= 0x800;
  data->initialX = gPostBootScrollRanges[index - 11][0];
  data->targetX = gPostBootScrollRanges[index - 11][1];
  {
    DbaaU16 target = data->targetX;
    int initial = data->initialX;
    initialFixed = (DbaaU32)initial << 16;
    data->position = initialFixed;
    delta = (DbaaU32)((DbaaS16)target - initial) << 17;
  }
  data->velocity = delta / duration;
  data->acceleration = (int)(0u - (DbaaU32)delta) / (duration * duration);
  gBackgroundScroll[data->background][0] = (int)initialFixed >> 16;
  return task;
}
