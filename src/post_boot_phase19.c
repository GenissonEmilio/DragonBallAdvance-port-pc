#include "post_boot.h"
/* USA 0x080EFFFC: 68 complete bytes match the ROM. */
void PostBoot_Phase19(struct DbaaPostBootData *data) {
  if (!(data->flags & 1)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      if (PostBoot_StartFade(data, 1)) {
        data->tileChunk = 0;
        data->phase = PostBoot_CopyTileChunk;
      }
    }
  }
}
