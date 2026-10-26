#ifndef DBAA_SERIAL_H
#define DBAA_SERIAL_H

#include "game_state.h"

struct SerialState {
  DbaaU8 unknown00[2], mode, unknown03[5];
  DbaaU8 flags, unknown09[0xB];
  DbaaU32 word14;
  DbaaU8 unknown18[0x10];
  void *sendA, *sendB, *receiveA[4], *receiveB[4], *receiveC[4];
  DbaaU8 storage[0x188];
};
extern struct SerialState gSerialState;
extern DbaaU8 gSerialAuxByte, gSerialAuxState[12];
/* The twelve-byte auxiliary block, also exposed as gSerialAuxState. */
struct SerialHandshake {
  DbaaU8 lane, unknown01;
  DbaaU16 step, sendWord, expectedWord, unknown08, status;
};
extern struct SerialHandshake gSerialHandshake;
extern DbaaU32 gSerialLastReceived, gSerialLastSent;
extern DbaaU32 gSerialPacketValue;
extern const DbaaU16 gSerialHandshakeSequence[];
int Serial_ProcessPacket(DbaaU32 stage);
DbaaU8 Serial_ValidatePacket(void);
DbaaU32 Serial_MakePacket(DbaaU32 stage);
void Func_08114D70(void);
void Serial_Stop(void);
void Serial_Start(void);
void Serial_InstallHandlerAndStart(void);
void Serial_IrqHandler(void);

#endif
