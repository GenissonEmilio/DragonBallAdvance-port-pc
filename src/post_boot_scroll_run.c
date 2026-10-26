#include "backgrounds.h"
#include "post_boot.h"
/* USA 0x080EF8B8: 152 complete bytes match the ROM. */
void PostBoot_ScrollRun(void) {
  struct DbaaPostBootScrollData *data =
      (struct DbaaPostBootScrollData *)SEQUENCE_DATA(gCurrentTask);
  data->velocity += data->acceleration;
  data->position += data->velocity;
  gBackgroundScroll[data->background][0] = data->position >> 16;
  data->elapsed++;
  if (data->elapsed >= data->duration) {
    struct DbaaPostBootData *parent = data->parent;
    parent->scrollTasks[data->slot] = 0;
    if (!parent->scrollTasks[(data->slot + 1) & 1])
      parent->flags &= ~0x800;
    Task_Destroy(gCurrentTask);
  }
}
