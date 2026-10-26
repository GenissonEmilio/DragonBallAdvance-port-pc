#include "services.h"
void Func_080A38CC(void)
{
    volatile DbaaU32 fill=0;
    DMA_START_READBACK(&fill,gGameData0202A0C0,0x85004000);
}
