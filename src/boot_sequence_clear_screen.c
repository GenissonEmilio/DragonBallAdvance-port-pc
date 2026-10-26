#include "sequences.h"
/* USA 0x080F35AC: 68 complete bytes match the ROM. */
void BootSequence_ClearScreen(DbaaU8 screen) {
  const struct DbaaBootScreen *entry = &gBootSequenceScript[screen];
  DbaaU16 mapBase = (gBgControlShadow[entry->background] >> 8) & 31;
  DbaaU16 zero;
  DbaaU16 *source = &zero;
  /* Keep the scratch address live before its zero store. */
  __asm__("" : : "r"(source));
  *source = 0;
  Bios_CpuSet(source, (void *)(0x06000000 + mapBase * 0x800), 0x01000400);
}
