#include "serial.h"
#include "services.h"
void Serial_Start(void) {
  IO16(0x04000208) = 0;
  IO16(0x04000200) &= 0xFF3F;
  IO16(0x04000208) = 1;
  IO16(0x04000134) = 0;
  IO16(0x04000128) = 0x1008;
  IO16(0x04000128) |= 0x4000;
  IO16(0x04000202) = 0xC0;
  IO16(0x04000208) = 0;
  IO16(0x04000200) |= 0xC0;
  IO16(0x04000208) = 1;
  {
    DbaaU32 value = (*(volatile DbaaU8 *)0x04000128);
    value &= ~1;
    (*(volatile DbaaU8 *)0x04000128) = value;
  }
  gSerialAuxByte = 0;
  {
    DbaaU32 zero = 0;
    Bios_CpuSet(&zero, gSerialAuxState, 0x05000003);
  }
  IO16(0x04000208) = 0;
  IO16(0x04000128) |= 0x80;
  IO16(0x04000208) = 1;
  IO16(0x0400010C) = 0x8000;
  IO16(0x0400010E) = 0xC1;
}
