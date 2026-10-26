#include "post_boot.h"
/* USA 0x080EEA7C: 148 complete bytes match the ROM. */
void PostBoot_Phase30(struct DbaaPostBootData *data) {
  struct DbaaPostBootFadeData config;
  if (!(data->flags & 2)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      if (!data->fade) {
        Runtime_Memset(&config, 0, sizeof(config));
        config.control = 0xEF;
        config.alpha = 0;
        config.start = 16;
        config.target = 0;
        config.duration = gPostBootTimeline[data->step] - data->elapsed;
        data->step++;
        PostBoot_CreateFade(data, &config);
        data->flags |= 0x10;
        data->child0 = PostBoot_CreateCurtain(data);
        data->phase = PostBoot_Phase31;
      }
    }
  }
}
