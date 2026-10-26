#include "serial.h"
/* USA 0x08115108: complete 60-byte function, including literals and padding. */

DbaaU8 Serial_ValidatePacket(void) {
  DbaaU32 data = gSerialLastReceived >> 4;
  DbaaU32 expected = gSerialLastReceived & 0xF;
  /* Keep the shifted data as the source of the header nibble. */
  DbaaU32 checksum = ({
    __asm__("" : "+r"(data));
    data >> 24;
  });
  DbaaU8 index = 6;
  for (; index != 0; index--)
    checksum ^= (data >> ((index - 1) * 4)) & 0xF;
  if (checksum == expected)
    return 0;
  return 1;
}
