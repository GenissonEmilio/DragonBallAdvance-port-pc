#include "services.h"
void Func_080A30F8(void)
{
    volatile DbaaU32 fill=0;
    DMA_START_READBACK(&fill,&gGameWord02024774,0x85000001);
    Func_080A32DC(); Func_080A6DF0(); Func_080A7BA0(); Func_080A3B88();
}
