#include "post_boot.h"
/* USA 0x080EED40: 116 complete bytes match the ROM. */
void PostBoot_Phase47(struct DbaaPostBootData *data) {
  struct DbaaPostBootFadeData config;
  if (!(data->flags & 1)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      Runtime_Memset(&config, 0, sizeof(config));
      config.control = 0xBF;
      config.alpha = 0;
      config.start = 0;
      config.target = 16;
      config.duration = gPostBootTimeline[data->step] - data->elapsed;
      PostBoot_CreateFade(data, &config);
      data->flags |= 0x10;
      data->phase = PostBoot_Phase48;
    }
  }
}
