#ifndef DBAA_RUNTIME_H
#define DBAA_RUNTIME_H

#include "game_state.h"

extern DbaaU32 gSystemFlags;
extern DbaaU32 gPreviousSystemFlags;
extern DbaaU8 gFrameBeginByte;
extern DbaaU8 gFrameMode;
extern DbaaU8 gInputMode;
extern DbaaU8 gAfterVBlankByte;
extern DbaaU8 gInputBufferA[];
extern DbaaU8 gInputBufferB[];
extern DbaaU32 gInputResult;
extern DbaaU16 gVideoWords[];
extern DbaaU16 gDisplayControlShadow;
extern const void *gUnknownData03003BE4;
extern const void *gUnknownData030030D0;

void Runtime_Initialize(void);
void Runtime_MainLoop(void);
void Runtime_Startup(void);
void Game_Entry(void);
void Game_Bootstrap(void);
void Game_ResetVideoState(void);
void Game_ResetVideoStateCallback(void);
int Game_Initialize(void);
void Game_CreateCounterTask(void);
void Input_Update(void);
void Tasks_RunFrame(void);
void Bios_VBlankIntrWait(void);
void Bios_CpuSet(const void *source, void *destination, DbaaU32 control);

void Func_0810D3E8(void);
void Func_08000354(void);
DbaaU32 Func_08113DD4(void *first, void *second, DbaaU32 mode);
int Func_08000440(void);
void Func_0800113C(void);
void Func_0811545C(void);
void Graphics_CommitCpu(void);
void Graphics_ClearOamCpu(void);
void Graphics_CommitDma(void);
void Graphics_ClearOamDma(void);
void Func_0810ADAC(void);
void Func_080C863C(DbaaU16 id, DbaaU8 step, DbaaU8 mode, void (*onComplete)(void));

#define REG_DISPSTAT (*(volatile DbaaU16 *)0x04000004)

#endif
