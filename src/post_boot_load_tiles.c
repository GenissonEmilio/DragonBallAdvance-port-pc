#include "post_boot.h"
/* USA 0x080F0434: 116 complete bytes match the ROM. */
void PostBoot_LoadTiles(DbaaU8 index) {
  const struct DbaaPostBootBackground *entry = &gPostBootBackgrounds[index];
  DbaaU8 bg = entry->background;
  DbaaU16 id;
  const void *tiles;
  DbaaU16 charBase;
  if (entry->backgroundId >= 0)
    id = entry->backgroundId;
  else
    id = gPostBootDefaultBackground;
  tiles = gBootBackgrounds[id]->tiles;
  charBase = (gBgControlShadow[bg] >> 2) & 3;
  if (index != 8)
    Bios_LZ77UnCompVram(tiles, (void *)(0x06000000 + charBase * 0x4000));
  else
    Bios_LZ77UnCompVram(tiles, (void *)0x06012000);
}
