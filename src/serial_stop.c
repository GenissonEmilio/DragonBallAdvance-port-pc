#include "serial.h"
#include "services.h"
void Serial_Stop(void) {
  IO16(0x04000208) = 0;
  IO16(0x04000200) &= 0xFF3F;
  IO16(0x04000208) = 1;
  IO16(0x04000128) = 0x2003;
  IO32(0x0400010C) = 0xBBBC;
  IO16(0x04000202) = 0xC0;
  gSerialState.flags &= 0x7F;
}
