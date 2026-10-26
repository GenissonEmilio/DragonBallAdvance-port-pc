#include "serial.h"
#include "services.h"
void Func_08114D70(void) {
  gInputMode = 0;
  gSystemFlags &= ~0x10000;
  Serial_Stop();
  Func_08113CE0(0);
  if (gSystemFlags & 0x80000)
    Serial_InstallHandlerAndStart();
}
