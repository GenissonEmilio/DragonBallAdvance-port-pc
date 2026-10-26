#include "post_boot.h"
/* USA 0x080EF754: 88 complete bytes match the ROM. */
void PostBoot_CurtainHold(void) {
  struct DbaaPostBootCurtainData *data =
      (struct DbaaPostBootCurtainData *)SEQUENCE_DATA(gCurrentTask);
  struct DbaaPostBootSprite *sprite = data->sprite1;
  DbaaU16 x;
  /* The empty r0 constraint emits no instruction. */
  for (x = (DbaaU16)-32; (DbaaS16)x <= 271;
       x = (((DbaaU32)x << 16) + 0x00200000) >> 16) {
    sprite->x = x;
    sprite->y = ({
      register DbaaU32 value __asm__("r0") = 80;
      __asm__("" : : "r"(value));
      value;
    });
    Graphics_DrawSprite(sprite);
  }
}
