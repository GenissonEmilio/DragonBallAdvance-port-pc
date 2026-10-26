#include "backgrounds.h"
#include "sequences.h"
/* USA 0x080F3220: 328 complete bytes match the ROM. */
void BootSequence_LoadScreen(DbaaU8 screen) {
  const struct DbaaBootScreen *entry = &gBootSequenceScript[screen];
  DbaaU8 bg = entry->background;
  /* Keep the script pointer across the register allocation boundary.
   * This empty constraint emits no instruction and reserves r9 here only. */
  DbaaU16 id = ({
    __asm__("" : : : "r9");
    entry->backgroundId;
  });
  const struct DbaaBootBackground *asset = gBootBackgrounds[id];
  const void *tiles = asset->tiles;
  const DbaaU16 *map = asset->tilemap;
  DbaaU32 control = (DbaaU32)gBgControlShadow[bg] << 16;
  DbaaU16 charBase = (control >> 18) & 3;
  void *mapVram = (void *)(0x06000000 + ((control >> 24) & 31) * 0x800);
  DbaaU8 width = asset->width;
  DbaaU8 height = asset->height;
  DbaaU16 row;
  Bios_LZ77UnCompVram(tiles, (void *)(0x06000000 + charBase * 0x4000));
  for (row = 0; row < height; row++) {
    DbaaU32 count = (width * 2) >> 1;
    Bios_CpuSet(&map[width * row], (DbaaU16 *)mapVram + row * 32,
                count & 0x1FFFFF);
  }
  if (gSystemFlags & 0x10000) {
    Func_08114668(gBootBackgrounds[id]->palette, (entry->palette & 15) * 16,
                  gBootBackgrounds[id]->paletteHalfwords);
  } else {
    DMA3.source = gBootBackgrounds[id]->palette;
    DMA3.destination = gBgPaletteBuffer + entry->palette * 32;
    {
      const struct DbaaBootBackground **entryPointer = &gBootBackgrounds[id];
      /* Reload the asset pointer after setting the DMA destination. */
      __asm__("" : "+r"(entryPointer));
      DMA3.control = (*entryPointer)->paletteHalfwords | 0x80000000;
    }
    (void)DMA3.control;
    gSystemFlags |= 1;
  }
  *(DbaaU16 *)gBgPaletteBuffer = 0;
  gSystemFlags |= 1;
  gBackgroundScroll[bg][0] = entry->scrollX;
  gBackgroundScroll[bg][1] = entry->scrollY;
}
