#include "post_boot.h"
/* USA 0x080EF568: 232 complete bytes match the ROM. */
struct DbaaTask *PostBoot_CreateCurtain(struct DbaaPostBootData *parent) {
  struct DbaaTask *task;
  struct DbaaPostBootCurtainData *data;
  DbaaU16 zero;
  if (parent->child0)
    return 0;
  gDisplayControlShadow |= 0x1000;
  task = Task_Create(PostBoot_CurtainWait, 24, 0x300, 0,
                     PostBoot_CurtainOnDestroy);
  data = (struct DbaaPostBootCurtainData *)SEQUENCE_DATA(task);
  {
    DbaaU16 *source = &zero;
    /* Preserve the scratch address before its zero store. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, data, 0x0100000C);
  }
  data->sprite0 = &parent->sprites[0];
  data->sprite1 = &parent->sprites[1];
  data->x = 0x4400;
  data->y = 0x1400;
  data->velocityX = -608;
  data->velocityY = 0;
  data->background = parent->backgrounds[9].background;
  data->parent = parent;
  parent->child0 = task;
  gDisplayControlShadow |= 0x2000;
  gWindowShadow[0] = 0xFF;
  gWindowShadow[2] = 0xFF;
  gWindowShadow[4] = 0x3F;
  gWindowShadow[5] = 0x3F & ~(1 << data->background);
  return task;
}
