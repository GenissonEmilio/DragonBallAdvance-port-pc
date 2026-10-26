#include "post_boot.h"
/* USA 0x080EF950: 108 complete bytes match the ROM. */
void PostBoot_PositionRing(struct DbaaPostBootRingData *data, int angle,
                           DbaaU16 radius) {
  struct DbaaPostBootSprite *sprites = data->sprites;
  DbaaU32 shifted = (DbaaU32)angle << 22;
  DbaaU16 base;
  DbaaU8 i = 0;
  /* Retain the unsigned shift and zero index before extracting the base. */
  __asm__("" : "+r"(shifted), "+r"(i));
  base = shifted >> 22;
  do {
    DbaaU32 offset = 146 * i + 110;
    DbaaU16 phase;
    int x, y;
    /* Keep the per-sprite offset before adding the common angle. */
    __asm__("" : "+r"(offset));
    phase = (offset + base) & 0x3FF;
    x = ((radius * gSineTable[phase + 256]) >> 14) + 120;
    y = ((radius * gSineTable[phase]) >> 14) + 80;
    sprites[i].x = x;
    sprites[i].y = y;
    i++;
  } while (i < 7);
}
