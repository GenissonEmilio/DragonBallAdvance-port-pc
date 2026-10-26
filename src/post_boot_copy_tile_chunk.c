#include "post_boot.h"
/* USA 0x080EE990: 108 complete bytes match the ROM. */
void PostBoot_CopyTileChunk(struct DbaaPostBootData *data) {
  if (!(data->flags & 1)) {
    DbaaU8 bg = data->backgrounds[8].background;
    DbaaU16 charBase = (gBgControlShadow[bg] >> 2) & 3;
    Bios_CpuSet(
        (void *)(0x06012000 + (data->tileChunk << 12)),
        (void *)(0x06000000 + charBase * 0x4000 + (data->tileChunk << 12)),
        0x04000400);
    data->tileChunk++;
    if (data->tileChunk > 5) {
      data->tileChunk = 0;
      data->phase = PostBoot_Phase21;
    }
  }
}
