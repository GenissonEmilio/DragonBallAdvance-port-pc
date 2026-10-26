/* USA 0x081100DC: 188 complete bytes match the ROM. */
#include "sprites.h"
int SpriteCommand_Hitbox(const int *words, struct DbaaPostBootSprite *object) {
  /* Empty constraints retain register lifetimes; every operation is C. */
  register const int *command __asm__("r3") = words;
  register struct DbaaPostBootSprite *incoming __asm__("r1") = object;
  struct DbaaPostBootSprite *sprite;
  DbaaU32 index;
  register DbaaU8 *bytes __asm__("r3");
  volatile DbaaU32 *dma;
  __asm__("" : "+r"(command), "+r"(incoming));
  sprite = incoming;
  index = command[1] & 15;
  bytes = (DbaaU8 *)command;
  __asm__("" : "+r"(bytes));
  sprite->animationCursor += 3;
  dma = (volatile DbaaU32 *)0x040000D4;
  {
    register DbaaU32 source __asm__("r0") = (DbaaU32)(command + 1);
    __asm__("" : "+r"(source));
    dma[0] = source;
  }
  dma[1] = (DbaaU32)sprite + 32 + index * 8;
  dma[2] = 0x84000002;
  (void)dma[2];
  if (bytes[8] == bytes[10] && bytes[9] == bytes[11]) {
    register DbaaU8 *base __asm__("r0") = (DbaaU8 *)sprite + 32;
    __asm__("" : "+r"(base));
    base += index * 8;
    __asm__("" : "+r"(base));
    *(int *)base = -1;
  } else {
    if (sprite->flags & 0x800) {
      DbaaU8 *top = (DbaaU8 *)sprite + index * 8 + 0x25;
      DbaaU8 *bottom = (DbaaU8 *)sprite + index * 8 + 0x27;
      *top ^= *bottom;
      *bottom ^= *top;
      *top = -(*top ^ *bottom);
      *bottom = -*bottom;
    }
    if (sprite->flags & 0x400) {
      DbaaU8 *left = (DbaaU8 *)sprite + index * 8 + 0x24;
      DbaaU8 *right = (DbaaU8 *)sprite + index * 8 + 0x26;
      *left ^= *right;
      *right ^= *left;
      *left = -(*left ^ *right);
      *right = -*right;
    }
  }
  return 1;
}
