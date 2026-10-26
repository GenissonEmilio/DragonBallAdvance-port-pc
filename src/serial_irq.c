#include "serial.h"
#include "services.h"
/* USA 0x08114E6C: timer/serial callback. The seven empty constraints and
 * fixed-register temporaries preserve agbcc allocation without emitting code.
 */
void Serial_IrqHandler(void) {
  gSerialLastReceived = IO32(0x04000120);
  IO16(0x0400010E) = 0;
  IO16(0x0400010C) = 0x8000;
  switch (gSerialAuxByte) {
  case 0: {
    DbaaU32 first;
    volatile DbaaU32 *sio;
    register DbaaU32 data __asm__("r6");
    register DbaaU32 second __asm__("r6");
    /* Retain the I/O address across the packet-builder call. */
    {
      register volatile DbaaU32 *io __asm__("r0") = (void *)0x04000120;
      __asm__("" : : "r"(io));
      sio = io;
      data = *io;
    }
    {
      register DbaaU32 lane __asm__("r1") = gSerialHandshake.lane;
      register DbaaU32 shift __asm__("r2") = lane * 16;
      register DbaaU32 firstRegister __asm__("r0") = data;
      firstRegister <<= shift;
      firstRegister >>= 16;
      /* Keep the lane result in r0 while extracting the other lane. */
      __asm__("" : "+r"(firstRegister));
      data <<= (1 - lane) * 16;
      {
        register DbaaU32 shifted __asm__("r1") = data;
        __asm__("" : : "r"(shifted));
        second = shifted >> 16;
      }
      __asm__("" : : "r"(firstRegister));
      first = firstRegister;
    }
    if (gSerialHandshake.status == 0) {
      register DbaaU32 expected __asm__("r2") = gSerialHandshake.expectedWord;
      register DbaaU32 firstCopy __asm__("r1") = first;
      if (firstCopy == expected) {
        if (gSerialHandshake.step <= 3) {
          if (firstCopy == (DbaaU16)~gSerialHandshake.sendWord &&
              second == ({
                register DbaaU32 complement __asm__("r0") = (DbaaU16)~expected;
                __asm__("" : "+r"(complement));
                complement;
              }))
            gSerialHandshake.step++;
        } else {
          gSerialHandshake.status = second;
          if (second == 0x8002) {
            gSerialAuxByte = 1;
            gSerialLastSent = Serial_MakePacket(1);
            *sio = gSerialLastSent;
            gSerialHandshake.step = 0;
            break;
          }
          gSerialHandshake.status = 0;
          gSerialHandshake.step = 0;
        }
      } else
        gSerialHandshake.step = 0;
    }
    {
      register DbaaU32 step __asm__("r0") = gSerialHandshake.step;
      if (step <= 3) {
        step <<= 1;
        __asm__("" : : "r"(step));
        gSerialHandshake.sendWord =
            *(const DbaaU16 *)((const DbaaU8 *)gSerialHandshakeSequence + step);
      } else
        gSerialHandshake.sendWord = 0x8000;
    }
    gSerialHandshake.expectedWord = ~second;
    /* Preserve the original non-destructive complement into another register.
     */
    __asm__("" : : "r"(second));
    IO32(0x04000120) =
        (gSerialHandshake.sendWord << ((1 - gSerialHandshake.lane) * 16)) +
        (gSerialHandshake.expectedWord << (gSerialHandshake.lane * 16));
    break;
  }
  case 1:
    if (Serial_ProcessPacket(gSerialAuxByte)) {
      DbaaU32 zero;
      gSerialHandshake.step = 0;
      zero = 0;
      Bios_CpuSet(&zero, &gSerialHandshake, 0x05000003);
      gSerialAuxByte = 0;
    } else
      gSerialAuxByte = 2;
    gSerialLastSent = Serial_MakePacket(gSerialAuxByte);
    IO32(0x04000120) = gSerialLastSent;
    break;
  case 2:
    if (Serial_ProcessPacket(gSerialAuxByte)) {
      DbaaU32 zero;
      gSerialHandshake.step = 0;
      zero = 0;
      Bios_CpuSet(&zero, &gSerialHandshake, 0x05000003);
      gSerialAuxByte = 0;
    } else
      gSerialAuxByte = 3;
    gSerialLastSent = Serial_MakePacket(gSerialAuxByte);
    IO32(0x04000120) = gSerialLastSent;
    break;
  case 3:
    if (Serial_ProcessPacket(gSerialAuxByte)) {
      DbaaU32 zero;
      gSerialHandshake.step = 0;
      zero = 0;
      Bios_CpuSet(&zero, &gSerialHandshake, 0x05000003);
      gSerialAuxByte = 0;
    }
    gSerialLastSent = Serial_MakePacket(gSerialAuxByte);
    IO32(0x04000120) = gSerialLastSent;
    break;
  case 4:
  case 5:
  default:
    IO16(0x04000208) = 0;
    IO16(0x04000200) &= 0xFF7F;
    IO16(0x04000208) = 1;
    return;
  }
  IO16(0x04000128) |= 0x80;
  IO16(0x0400010E) = 0xC1;
}
