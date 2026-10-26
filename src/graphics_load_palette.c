/* USA 0x08114668: 168 complete bytes match the ROM. */
#include "graphics.h"
extern DbaaU16 gColorComponents[3][32];
#define IN_REGISTER(reg, expression)                                           \
  ({                                                                           \
    register DbaaU32 dbaaRegisterValue __asm__(reg) = (DbaaU32)(expression);   \
    __asm__("" : "+r"(dbaaRegisterValue));                                     \
    dbaaRegisterValue;                                                         \
  })
void Graphics_LoadBgPalette(const void *palette, DbaaU8 offset, DbaaU32 count) {
  register DbaaU32 first __asm__("r8") = offset;
  DbaaU16 i, length;
  __asm__("" : : "r"(first));
  length = (DbaaU16)IN_REGISTER("r2", count);
  i = 0;
  if (i < length) {
    register const DbaaU16 *components __asm__("r12") =
        (const DbaaU16 *)IN_REGISTER("r0", gColorComponents);
    register DbaaU32 blueMask __asm__("r10") = IN_REGISTER("r0", 0x7C00);
    register const DbaaU16 *blue __asm__("r9") = (const DbaaU16 *)IN_REGISTER(
        "r0", IN_REGISTER("r0", 128) + (DbaaU32)components);
    do {
      register DbaaU32 position __asm__("r4") =
          (DbaaU32)IN_REGISTER("r0", first) + i;
      DbaaU16 *destination;
      register DbaaU32 color __asm__("r3");
      register const DbaaU16 *red __asm__("r2");
      register DbaaU32 green __asm__("r0");
      register DbaaU32 merged __asm__("r1");
      __asm__("" : "+r"(position));
      destination = (DbaaU16 *)gBgPaletteBuffer + position;
      color = *(const DbaaU16 *)palette;
      __asm__("" : "+r"(color));
      red = components + (color & 0x1F);
      __asm__("" : "+r"(red));
      green = (color & 0x3E0) >> 4;
      __asm__("" : "+r"(green));
      green += IN_REGISTER("r1", (DbaaU8 *)components + 64);
      __asm__("" : "+r"(green));
      merged = *red | *(const DbaaU16 *)green;
      __asm__("" : "+r"(merged));
      green = (IN_REGISTER("r0", blueMask) & color) >> 9;
      green += (DbaaU32)blue;
      __asm__("" : "+r"(green));
      merged |= *(const DbaaU16 *)green;
      *destination = merged;
      palette = (const DbaaU8 *)palette + 2;
      i++;
    } while (i < length);
  }
  {
    register DbaaPaletteCallback callback __asm__("r3") =
        *(DbaaPaletteCallback *)IN_REGISTER("r0", &gPaletteCallback);
    __asm__("" : "+r"(callback));
    if (callback)
      Palette_CallCallback(gBgPaletteBuffer, first, length, callback);
  }
  gSystemFlags |= 1;
}
