/* Readable algorithm reference for USA 0x080EEDB4.
 * This structured version does NOT have byte matching and is not a production
 * build target. The matched GNU C register-flow source is
 * src/post_boot_load_background.c. Keep GBA hardware accesses for now.
 */
#include "backgrounds.h"
#include "post_boot.h"
void PostBoot_LoadBackground(DbaaU8 index) {
  const struct DbaaPostBootBackground *entry = &gPostBootBackgrounds[index];
  DbaaU8 bg = entry->background;
  DbaaU16 id;
  DbaaU32 control;
  const struct DbaaBootBackground *asset;
  const void *tiles;
  const DbaaU16 *map;
  DbaaU16 charBase;
  DbaaU16 *mapVram;
  DbaaU8 width, height;
  DbaaU16 row;
  if (entry->backgroundId >= 0)
    id = entry->backgroundId;
  else
    id = gPostBootDefaultBackground;
  if (index == 10) {
    PostBoot_LoadSpecialBackground(10);
  } else {
    control = gBgControlShadow[bg];
    control &= 0xFFFC;
    gBgControlShadow[bg] = control;
    control |= entry->priority;
    gBgControlShadow[bg] = control;
    asset = gBootBackgrounds[id];
    tiles = asset->tiles;
    map = asset->tilemap;
    charBase = ((control << 16) >> 18) & 3;
    mapVram = (DbaaU16 *)(0x06000000 + (((control << 16) >> 24) & 31) * 0x800);
    width = asset->width;
    height = asset->height;
    Bios_LZ77UnCompVram(tiles, (void *)(0x06000000 + charBase * 0x4000));
    if (entry->flip == 0) {
      for (row = 0; row < height; row++) {
        DbaaU32 count = (width * 2) >> 1;
        Bios_CpuSet(&map[width * row], mapVram + row * 32, count & 0x1FFFFF);
      }
    } else {
      const DbaaU16 *source = map;
      for (row = 0; row < height; row++) {
        DbaaU16 *destination = mapVram + row * 32 + width - 1;
        DbaaU8 col;
        for (col = 0; col < width; col++) {
          *destination = *source ^ 0x400;
          source++;
          destination--;
        }
      }
    }
    if (entry->sourcePalette != entry->destinationPalette) {
      DbaaU16 palette = (entry->destinationPalette & 15) << 12;
      for (row = 0; row < height; row++) {
        DbaaU16 *destination = mapVram + row * 32;
        DbaaU8 col;
        for (col = 0; col < width; col++) {
          *destination = (*destination & 0xFFF) | palette;
          destination++;
        }
      }
    }
    if (entry->paletteCount) {
      if (gSystemFlags & 0x10000) {
        Func_08114668((const DbaaU16 *)gBootBackgrounds[id]->palette +
                          entry->sourcePalette * 16,
                      (entry->destinationPalette & 15) * 16,
                      entry->paletteCount * 16);
      } else {
        DMA_START((const DbaaU16 *)gBootBackgrounds[id]->palette +
                      entry->sourcePalette * 16,
                  gBgPaletteBuffer + entry->destinationPalette * 32,
                  entry->paletteCount * 16 | 0x80000000);
        gSystemFlags |= 1;
      }
    }
    *(DbaaU16 *)gBgPaletteBuffer = 0;
    gSystemFlags |= 1;
    gBackgroundScroll[bg][0] = entry->scrollX;
    gBackgroundScroll[bg][1] = entry->scrollY;
  }
}
