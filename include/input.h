#ifndef DBAA_INPUT_H
#define DBAA_INPUT_H

#include "game_state.h"

extern DbaaU16 gHeldKeys;
extern DbaaU16 gRawHeldKeys;
extern DbaaU16 gPreviousKeys;
extern DbaaU16 gPressedKeys;
extern DbaaU16 gReleasedKeys;
extern DbaaU16 gRepeatKeys;
extern DbaaU8 gKeyRepeatTimers[];
extern DbaaU8 gKeyInitialDelays[];
extern DbaaU8 gKeyRepeatDelays[];
extern DbaaU8 gInputConfig[];

void Func_0811456C(DbaaU16 keys);
DbaaU16 Func_0811453C(void);

#define REG_KEYINPUT (*(volatile DbaaU16 *)0x04000130)

#endif
