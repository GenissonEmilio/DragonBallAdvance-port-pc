#include "post_boot.h"
/* USA 0x080EF448: 168 complete bytes match the ROM. */
struct DbaaPostBootFadeData *
PostBoot_CreateFade(struct DbaaPostBootData *parent,
                    const struct DbaaPostBootFadeData *config) {
  struct DbaaTask *task;
  struct DbaaPostBootFadeData *data;
  if (parent->fade)
    return 0;
  task = Task_Create(PostBoot_FadeRun, 20, 0x180, 0, PostBoot_FadeOnDestroy);
  data = (struct DbaaPostBootFadeData *)SEQUENCE_DATA(task);
  Bios_CpuSet(config, data, 10);
  data->elapsed = 0;
  data->increment = ((config->target - config->start) << 8) / config->duration;
  data->current = data->start << 8;
  data->parent = parent;
  parent->fade = data;
  parent->flags |= 0x10;
  gBlendShadow[0] = data->control;
  gBlendShadow[1] = data->alpha;
  gBlendShadow[2] = data->start;
  return data;
}
