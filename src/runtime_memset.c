/* USA 0x08118508: 84 complete bytes match the ROM. */
#include "runtime.h"
void *Runtime_Memset(void *destination, int value, DbaaU32 size) {
  DbaaU8 *bytes = destination;
  if (size > 3 && !((DbaaU32)bytes & 3)) {
    DbaaU32 *words = destination;
    DbaaU32 fill;
    value &= 0xFF;
    fill = value << 8;
    fill |= value;
    fill |= fill << 16;
    while (size > 15) {
      *words++ = fill;
      *words++ = fill;
      *words++ = fill;
      *words++ = fill;
      size -= 16;
    }
    while (size > 3) {
      *words++ = fill;
      size -= 4;
    }
    bytes = (DbaaU8 *)words;
  }
  while (1) {
    register DbaaU32 remaining __asm__("r0") = size;
    size--;
    /* Keep the pre-decrement count used by the byte-tail branch. */
    __asm__("" : "+r"(remaining));
    if (!remaining)
      break;
    *bytes++ = value;
  }
  return destination;
}
