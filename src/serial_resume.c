#include "serial.h"
#include "services.h"
void Serial_InstallHandlerAndStart(void) {
  IO16(0x04000208) = 0;
  gIrqHandlers[0] = (DbaaU32)Serial_IrqHandler;
  IO16(0x04000208) = 1;
  Serial_Start();
}
