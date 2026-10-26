#include "services.h"
extern DbaaU32 gVideoBufferTailWord;
extern DbaaU8 gVideoAuxBuffer[];
void Func_08000FDC(void) {
  DbaaU16 zeroA, zeroB;
  gVideoBufferTailWord = 0;
  zeroA = 0;
  Bios_CpuSet(&zeroA, gVideoWords, 0x0100015C);
  zeroB = 0;
  Bios_CpuSet(&zeroB, gVideoAuxBuffer, 0x01000016);
}
