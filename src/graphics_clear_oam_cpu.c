#include "graphics.h"

extern DbaaU8 gScanlineBufferA[];

void Graphics_ClearOamCpu(void)
{
    DbaaU32 fill;
    gGraphicsByte03002BF0 = 0;
    gSystemFlags &= ~8;
    if ((gSystemFlags & 0x20) == 0)
    {
        if (gScanlineWriteBuffer == gScanlineBufferA)
        {
            gScanlineWriteBuffer = gScanlineBufferA + 0x280;
            gScanlineReadBuffer = gScanlineBufferA;
        }
        else
        {
            gScanlineWriteBuffer = gScanlineBufferA;
            gScanlineReadBuffer = gScanlineBufferA + 0x280;
        }
    }
    gSystemFlags &= ~4;
    fill = 0x200;
    Bios_CpuFastSet(&fill, gOamBuffer, 0x01000100);
    gGraphicsByte030065E0 = 0;
    gSystemFlags &= ~0x10;
}
