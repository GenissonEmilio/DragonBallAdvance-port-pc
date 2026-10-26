#include "graphics.h"

void Graphics_CommitCpu(void)
{
    DbaaU8 i = 0;
    DbaaU32 fillA;
    DbaaU32 fillB;

    IO16(0x04000000) = gDisplayControlShadow;
    Bios_CpuSet(gBgControlShadow, (void *)0x04000008, 0x04000002);
    if (gSystemFlags & 1)
    {
        Bios_CpuFastSet(gBgPaletteBuffer, (void *)0x05000000, 0x80);
        gSystemFlags ^= 1;
    }
    if (gSystemFlags & 2)
    {
        Bios_CpuFastSet(gObjPaletteBuffer, (void *)0x05000200, 0x80);
        gSystemFlags ^= 2;
    }
    Bios_CpuSet(gWindowShadow, (void *)0x04000040, 0x04000003);
    Bios_CpuSet(gBlendShadow, (void *)0x04000050, 3);
    Bios_CpuSet(gBgScrollShadow, (void *)0x04000010, 8);
    Bios_CpuSet(gBgAffineShadow, (void *)0x04000020, 0x04000008);
    if (gSystemFlags & 8)
    {
        IO16(0x04000200) |= 2;
        fillA = i;
        Bios_CpuFastSet(&fillA, &gGraphicsByte03003F80, 0x01000004);
        if (gGraphicsByte03002BF0 != 0)
            Bios_CpuFastSet(&gGraphicsByte03003B30, &gGraphicsByte03003F80,
                            gGraphicsByte03002BF0);
        gGraphicsByte03002C54 = gGraphicsByte03002BF0;
    }
    else
    {
        IO16(0x04000200) &= ~2;
        gGraphicsByte03002C54 = i;
    }
    if (gFrameMode == 0xFF)
    {
        Graphics_ProcessOam();
        Bios_CpuFastSet(gOamBuffer, (void *)0x07000000, 0x100);
    }
    {
        DbaaU8 callbackIndex;
        for (callbackIndex = 0; callbackIndex < gGraphicsByte03002CB8; callbackIndex++)
            gGraphicsFrameCallbacks[callbackIndex]();
    }
    if (gSystemFlags & 0x10)
    {
        fillB = 0;
        Bios_CpuFastSet(&fillB, gGraphicsFrameCallbacks, 0x01000006);
        if (gGraphicsByte030065E0 != 0)
            Bios_CpuFastSet(&gGraphicsByte03002BD0, gGraphicsFrameCallbacks,
                            gGraphicsByte030065E0);
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
