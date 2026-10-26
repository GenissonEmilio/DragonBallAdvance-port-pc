#include "services.h"
struct VideoControlState {
  DbaaU8 unknown00[8];
  DbaaU16 half08;
};
extern struct VideoControlState gVideoControlState;
void Func_080010C4(void) { gVideoControlState.half08 = 0; }
