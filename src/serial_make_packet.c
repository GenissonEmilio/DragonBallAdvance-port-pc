#include "serial.h"
/* USA 0x08115144: complete 236-byte function, including literals and padding.
 */
extern DbaaU8 gInitByte030065EC;
DbaaU32 Serial_MakePacket(DbaaU32 stage) {
  DbaaU32 packet;
  DbaaU32 checksum;
  DbaaU8 index;
  register DbaaU32 result __asm__("r1");
  /* Outside stages 1..5 the original returns incoming r1 unchanged.
   * Capture it explicitly instead of reading an uninitialized C object. */
  __asm__("" : "=r"(result));
  switch ((DbaaU8)stage) {
  case 1:
    packet = 0x10000010;
    checksum = (DbaaU8)(packet >> 28);
    for (index = 6; index != 0; index--)
      checksum ^= (packet >> (index * 4)) & 0xF;
    break;
  case 2:
    packet = ((gSerialPacketValue & 0xFFFFFF) << 4) | 0x20000000;
    /* Retain the packet and the explicit byte truncation of its type. */
    __asm__("" : "+r"(packet));
    {
      register DbaaU32 type __asm__("r0") = packet >> 28;
      __asm__("" : "+r"(type));
      checksum = (DbaaU8)type;
    }
    for (index = 6; index != 0; index--)
      checksum ^= (packet >> (index * 4)) & 0xF;
    break;
  case 3:
    packet = (gInitByte030065EC << 4) | 0x40000000;
    /* Retain the packet and the explicit byte truncation of its type. */
    __asm__("" : "+r"(packet));
    {
      register DbaaU32 type __asm__("r0") = packet >> 28;
      __asm__("" : "+r"(type));
      checksum = (DbaaU8)type;
    }
    for (index = 6; index != 0; index--)
      checksum ^= (packet >> (index * 4)) & 0xF;
    break;
  case 4:
  case 5:
    packet = 0x10000010;
    checksum = (DbaaU8)(packet >> 28);
    for (index = 6; index != 0; index--)
      checksum ^= (packet >> (index * 4)) & 0xF;
    break;
  default:
    goto finish;
  }
  result = 0xF;
  result &= checksum;
  result |= packet;
finish:
  return result;
}
