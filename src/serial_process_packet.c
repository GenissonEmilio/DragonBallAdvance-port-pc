#include "serial.h"
/* USA 0x0811509C: complete 108-byte function, including literals and padding.
 */

int Serial_ProcessPacket(DbaaU32 stage) {
  DbaaU8 current = stage;
  DbaaU32 type = gSerialLastReceived >> 28;
  if (Serial_ValidatePacket())
    return 1;
  switch (current) {
  case 1:
    gSerialPacketValue = ((gSerialLastReceived << 4) >> 8) & 1;
    if (type != 1)
      return 1;
    break;
  case 2:
    if (type != 2)
      return 1;
    if (gSerialPacketValue != ((gSerialLastReceived << 4) >> 8))
      return 1;
    break;
  case 3:
    if (type != 3)
      return 1;
    break;
  default:
    return 1;
  }
  return 0;
}
