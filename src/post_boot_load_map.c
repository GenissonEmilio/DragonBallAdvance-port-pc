#include "post_boot.h"
/* USA 0x080EEFE8: 316 complete bytes match the ROM. */
void PostBoot_LoadMap(DbaaU8 index) {
  const struct DbaaPostBootBackground *entry = &gPostBootBackgrounds[index];
  DbaaU8 bg = entry->background;
  DbaaU16 id;
  const struct DbaaBootBackground *asset;
  const DbaaU16 *map;
  DbaaU16 *mapVram;
  DbaaU8 width, height;
  DbaaU16 row;
  /* Reserve r9 here so the script stays in a low register. */
  __asm__("" : : : "r9");
  if (entry->backgroundId >= 0)
    id = entry->backgroundId;
  else
    id = gPostBootDefaultBackground;
  asset = gBootBackgrounds[id];
  map = asset->tilemap;
  mapVram =
      (DbaaU16 *)(0x06000000 + ((gBgControlShadow[bg] >> 8) & 31) * 0x800);
  width = asset->width;
  height = asset->height;
  if (entry->flip == 0) {
    for (row = 0; row < height; row++) {
      DbaaU32 count = (width * 2) >> 1;
      Bios_CpuSet(&map[width * row], mapVram + row * 32, count & 0x1FFFFF);
    }
  } else {
    const DbaaU16 *source = map;
    for (row = 0; row < height; row++) {
      /* Form the reversed row offset before adding its width. */
      DbaaU32 offset = row * 32 - 1;
      DbaaU16 *destination = ({
        __asm__("" : "+r"(offset));
        mapVram + (offset + width);
      });
      DbaaU8 col;
      for (col = 0; col < width; col++) {
        *destination = *source ^ 0x400;
        source++;
        destination--;
      }
    }
  }
  if (entry->sourcePalette != entry->destinationPalette) {
    /* Reload the selector after the source/destination comparison. */
    DbaaU16 palette = ({
      __asm__("" : "+r"(entry));
      (entry->destinationPalette & 15) << 12;
    });
    for (row = 0; row < height; row++) {
      DbaaU16 *destination = mapVram + row * 32;
      DbaaU8 col;
      for (col = 0; col < width; col++) {
        *destination = (*destination & 0xFFF) | palette;
        destination++;
      }
    }
  }
}
