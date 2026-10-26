#include "post_boot.h"
/* USA 0x080EE9FC: 128 complete bytes match the ROM. */
int PostBoot_StartFade(struct DbaaPostBootData *parent, DbaaU8 direction) {
  struct DbaaPostBootFadeData config;
  if (!parent->fade) {
    Runtime_Memset(&config, 0, sizeof(config));
    config.control = 0xFF;
    config.alpha = 0;
    config.duration = gPostBootTimeline[parent->step] - parent->elapsed;
    parent->step++;
    if (direction == 0) {
      config.start = 16;
      config.target = 0;
    } else {
      config.start = 0;
      config.target = 16;
    }
    PostBoot_CreateFade(parent, &config);
    parent->flags |= 0x10;
    return 1;
  }
  return 0;
}
