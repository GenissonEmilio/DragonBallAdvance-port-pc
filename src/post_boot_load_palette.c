#include "post_boot.h"
/* USA 0x080EF124: 188 complete bytes match the ROM. */
void PostBoot_LoadPalette(DbaaU8 index) {
  const struct DbaaPostBootBackground *entry = &gPostBootBackgrounds[index];
  DbaaU16 id;
  if (entry->backgroundId >= 0)
    id = entry->backgroundId;
  else
    id = gPostBootDefaultBackground;
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
}
