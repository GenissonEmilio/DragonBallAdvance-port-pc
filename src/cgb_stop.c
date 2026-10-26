/* USA 0x0810B834: 80 complete bytes match the ROM. */
#include "audio.h"
void Cgb_Stop(DbaaU8 channel) {
  switch (channel) {
  case 1:
    *(volatile DbaaU8 *)0x04000063 = 8;
    *(volatile DbaaU8 *)0x04000065 = 0x80;
    break;
  case 2:
    *(volatile DbaaU8 *)0x04000069 = 8;
    *(volatile DbaaU8 *)0x0400006D = 0x80;
    break;
  case 3:
    *(volatile DbaaU8 *)0x04000070 = 0;
    break;
  default:
    *(volatile DbaaU8 *)0x04000079 = 8;
    *(volatile DbaaU8 *)0x0400007D = 0x80;
    break;
  }
}
