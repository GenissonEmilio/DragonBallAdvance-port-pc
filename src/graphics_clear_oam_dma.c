#include "graphics.h"

extern DbaaU8 gScanlineBufferA[];

void Graphics_ClearOamDma(void)
{
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
    {
        volatile DbaaU16 fill = 0x200;
        DMA_START(&fill, gOamBuffer, 0x81000080);
    }
    {
        volatile DbaaU16 fill = 0x200;
        DMA_START(&fill, gOamBuffer + 0x100, 0x81000080);
    }
    {
        volatile DbaaU16 fill = 0x200;
        DMA_START(&fill, gOamBuffer + 0x200, 0x81000080);
    }
    {
        volatile DbaaU16 fill = 0x200;
        DMA_START(&fill, gOamBuffer + 0x300, 0x81000080);
    }
    gGraphicsByte030065E0 = 0;
    gSystemFlags &= ~0x10;
}
