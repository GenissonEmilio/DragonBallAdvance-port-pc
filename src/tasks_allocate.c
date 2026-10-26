#include "services.h"
struct DbaaTask *Tasks_AllocateSlot(void){if(gFreeTaskIndex>=128){return 0;}else{return gTaskHeads[gFreeTaskIndex++];}}
