#ifndef DBAA_INITIALIZATION_H
#define DBAA_INITIALIZATION_H

#include "graphics.h"
#include "input.h"

extern DbaaU32 gInitWord03003104;
extern DbaaU8 gInitByte03003F74;
extern DbaaU8 gInitByte03003D00;
extern DbaaU8 gInitByte03006C20;
extern DbaaU8 gInitByte030065E8;
extern DbaaU8 gInitByte03003F10;
extern DbaaU8 gInitData030030F0[];
extern DbaaU32 gInitWord03006610;
extern DbaaU8 gInitData03003130[];
extern DbaaU8 gInitByte03002C60;
extern DbaaU8 gInitByte03003F70;
extern DbaaU8 gInitData03002BB0[];
extern DbaaU8 gInitData030065F0[];
extern DbaaU16 gInitHalf03002CB4;
extern DbaaU16 gInitHalf03002B50;
extern DbaaU16 gInitHalf03006C24;
extern DbaaU16 gInitHalf03003F18;
extern DbaaU16 gInitHalf030065E4;
extern DbaaU16 gInitHalf03002CBC;
extern DbaaU16 gInitHalf03003BEC;
extern DbaaU16 gInitHalf03006C28;
extern DbaaU32 gInitWord03006C50;
extern DbaaU32 gInitWord03006C48;
extern DbaaU32 gInitWord030030D4;
extern DbaaU32 gIrqHandlers[];
extern DbaaU8 gIrqMainBuffer[];
extern const DbaaU32 gIrqDefaultHandlers[];
extern DbaaU8 gScanlineBufferA[];
extern DbaaU16 gGameHalf03002BEC;
extern void *gGamePointer03002CB0;
extern DbaaU8 gInitByte030065EC;
extern DbaaU32 gInitWord03002C50;
extern DbaaU8 gInitByte03002CC0;

void Func_08114BA4(void);
void Func_0810AD34(void);
void Func_0810B2D0(DbaaU32 value);
int Tasks_Initialize(void);
void Func_08115618(void);
void Func_08113C38(void);
DbaaU16 Func_081156FC(DbaaU16 value);
void Func_08113CE0(int value);

#endif
