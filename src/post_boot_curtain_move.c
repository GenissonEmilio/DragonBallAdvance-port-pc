#include "post_boot.h"
/* USA 0x080EF650: 260 complete bytes match the ROM. */
void PostBoot_CurtainMove(void) {
  /* Empty constraints retain the original value lifetimes and arguments. */
  struct DbaaPostBootCurtainData *data = ({
    register struct DbaaPostBootCurtainData *value __asm__("r0") =
        (struct DbaaPostBootCurtainData *)SEQUENCE_DATA(gCurrentTask);
    __asm__("" : "+r"(value));
    value;
  });
  DbaaU16 x, windowX;
  DbaaU32 packed, next;
  struct DbaaPostBootSprite *sprite;
  DbaaU16 drawX;
  DbaaU16 zero;
  data->x += data->velocityX;
  data->y += data->velocityY;
  x = data->x >> 6;
  /* Compare the signed coordinate through its packed 16-bit representation. */
  if ((int)((DbaaU32)x << 16) < (int)0xFFE00000) {
    data->parent->flags |= 0x400;
    gCurrentTask->callback = PostBoot_CurtainHold;
    gDisplayControlShadow &= 0xDFFF;
    {
      DbaaU16 *source = &zero;
      __asm__("" : : "r"(source));
      *source = 0;
      Bios_CpuSet(source, gWindowShadow, 0x01000006);
    }
  }
  __asm__("" : "+r"(x));
  {
    register DbaaU32 bits __asm__("r0") = (DbaaU32)x << 16;
    __asm__("" : "+r"(bits));
    windowX = bits >> 16;
    packed = bits;
  }
  if (windowX <= 255) {
    gWindowShadow[0] = x;
    if (((int)packed >> 16) <= 71) {
      data->parent->flags |= 0x200;
      gDisplayControlShadow &= ~(1 << (data->background + 8));
    }
  }
  sprite = data->sprite0;
  drawX = 240;
  sprite->x = data->x >> 6;
  sprite->y = data->y >> 6;
  Graphics_DrawSprite(sprite);
  sprite = data->sprite1;
  if ((DbaaS16)drawX > ((int)packed >> 16))
    do {
      sprite->x = drawX;
      sprite->y = ({
        register DbaaU32 value __asm__("r0") = 80;
        __asm__("" : : "r"(value));
        value;
      });
      Graphics_DrawSprite(sprite);
      next = ((DbaaU32)drawX << 16) + 0xFFE00000;
      drawX = next >> 16;
    } while ((int)next > (int)packed);
}
