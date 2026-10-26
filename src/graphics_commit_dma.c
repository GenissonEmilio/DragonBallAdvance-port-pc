#include "graphics.h"

void Graphics_CommitDma(void)
{
    DbaaU8 i = 0;
    DbaaU32 fill;

    IO16(0x04000000) = gDisplayControlShadow;
    DMA_START(gBgControlShadow, 0x04000008, 0x84000002);
    if (gSystemFlags & 1)
    {
        DMA_START(gBgPaletteBuffer, 0x05000000, 0x84000080);
        gSystemFlags ^= 1;
    }
    if (gSystemFlags & 2)
    {
        DMA_START(gObjPaletteBuffer, 0x05000200, 0x84000080);
        gSystemFlags ^= 2;
    }
    DMA_START(gWindowShadow, 0x04000040, 0x84000003);
    DMA_START(gBlendShadow, 0x04000050, 0x80000003);
    DMA_START(gBgScrollShadow, 0x04000010, 0x80000008);
    DMA_START(gBgAffineShadow, 0x04000020, 0x84000008);
    if (gSystemFlags & 8)
    {
        IO16(0x04000200) |= 2;
        fill = i;
        DMA_START(&fill, &gGraphicsByte03003F80, 0x85000004);
        if (gGraphicsByte03002BF0 != 0)
            DMA_START(&gGraphicsByte03003B30, &gGraphicsByte03003F80,
                      0x84000000 | gGraphicsByte03002BF0);
        gGraphicsByte03002C54 = gGraphicsByte03002BF0;
    }
    else
    {
        IO16(0x04000200) &= ~2;
        gGraphicsByte03002C54 = i;
    }
    if (gSystemFlags & 4)
        DMA_START(gScanlineWriteBuffer, gScanlineDmaDestination,
                  0x80000000 | (gScanlineByte02000518 >> 1));

    if (gFrameMode == 0xFF)
    {
        Graphics_ProcessOam();
        DMA_START(gOamBuffer, 0x07000000, 0x80000080);
        DMA_START(gOamBuffer + 0x100, 0x07000100, 0x80000080);
        DMA_START(gOamBuffer + 0x200, 0x07000200, 0x80000080);
        DMA_START(gOamBuffer + 0x300, 0x07000300, 0x80000080);
    }
    for (i = 0; i < gGraphicsByte03002CB8; i++)
        gGraphicsFrameCallbacks[i]();
    if (gSystemFlags & 0x10)
    {
        fill = 0;
        DMA_START(&fill, gGraphicsFrameCallbacks, 0x85000006);
        if (gGraphicsByte030065E0 != 0)
            DMA_START(&gGraphicsByte03002BD0, gGraphicsFrameCallbacks,
                      0x84000000 | gGraphicsByte030065E0);
        gGraphicsByte03002CB8 = gGraphicsByte030065E0;
    }
    else
        gGraphicsByte03002CB8 = 0;

    i = gFrameMode;
    if (i == 0xFF)
        i = 0;
    gFrameMode = 0xFF;
    for (; i < 4; i++)
    {
        if (gGraphicsCallbacks[i]() == 0)
        {
            gFrameMode = i;
            break;
        }
    }
}
