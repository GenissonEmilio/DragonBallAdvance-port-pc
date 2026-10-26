#include "post_boot.h"
/* USA 0x080EEB10: 156 complete bytes match the ROM. */
void PostBoot_Phase31(struct DbaaPostBootData *data) {
  struct DbaaPostBootFadeData config;
  if (!(data->flags & 2)) {
    if (data->elapsed >= gPostBootTimeline[data->step]) {
      data->step++;
      Runtime_Memset(&config, 0, sizeof(config));
      config.control = (1 << data->backgrounds[10].background) | 0xC0;
      config.alpha = 0;
      config.start = 16;
      config.target = 0;
      config.duration = 40;
      PostBoot_CreateFade(data, &config);
      data->flags |= 0x10;
      gDisplayControlShadow |= 1 << (data->backgrounds[10].background + 8);
      data->phase = PostBoot_Phase32;
    }
  }
}
