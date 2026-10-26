#include "initialization.h"

/* Scoped volatile fill sources retain the original DMA access order. */
#define FILL32(value_, dest_, control_) \
    { volatile DbaaU32 fill32 = (value_); DMA_START(&fill32, (dest_), (control_)); DMA_WAIT(); }
#define FILL16(value_, dest_, control_) \
    { volatile DbaaU16 fill16 = (value_); DMA_START(&fill16, (dest_), (control_)); DMA_WAIT(); }

void Runtime_Initialize(void)
{
    DbaaS16 i;

    IO16(0x04000208) = 0;
    IO16(0x04000204) = 0x4014;
    gSystemFlags = 0;
    gPreviousSystemFlags = 0;
    gInitWord03003104 = ~0;
    if ((IO16(0x04000134) & 0xC000) != 0x8000)
    {
        gSystemFlags = 0x200;
        DMA_START(0x06010000, 0x0203B000, 0x80002800);
        DMA_WAIT();
    }
    if (gHeldKeys == 0xF)
        gSystemFlags |= 0x1000;
    else
        gSystemFlags = 0;

    FILL32(0, 0x06000000, 0x85006000);
    FILL32(0, 0x07000000, 0x85000100);
    FILL32(0, 0x05000000, 0x85000100);
    gFrameMode = 0xFF;
    gInitByte03003F74 = 0;
    gInitByte03003D00 = 0;
    gInitByte03006C20 = 0;
    gInitByte030065E8 = 0;
    gInitByte03003F10 = 0;
    FILL32(0, gInitData030030F0, 0x85000004);
    gInitWord03006610 = 0;
    FILL32(0, gBgScrollShadow, 0x85000004);
    gSpriteOffset.x = 0;
    gSpriteOffset.y = 0;
    gDisplayControlShadow = 0x80;
    FILL32(0, gInitData03003130, 0x85000180);
    gInitByte03002C60 = 0;
    gInitByte03003F70 = 0;
    FILL16(0x200, gOamBuffer, 0x81000200);
    FILL16(0x200, gOamBufferAlternate, 0x81000200);
    FILL32(~0, gInitData03002BB0, 0x85000008);
    FILL32(~0, gInitData030065F0, 0x85000008);
    FILL32(0, gObjPaletteBuffer, 0x85000080);
    FILL32(0, gBgPaletteBuffer, 0x85000080);
    Func_08114BA4();

    gBgAffineShadow[0].pa = 0x100;
    gBgAffineShadow[0].pb = 0;
    gBgAffineShadow[0].pc = 0;
    gBgAffineShadow[0].pd = 0x100;
    gBgAffineShadow[0].x = 0;
    gBgAffineShadow[0].y = 0;
    gBgAffineShadow[1].pa = 0x100;
    gBgAffineShadow[1].pb = 0;
    gBgAffineShadow[1].pc = 0;
    gBgAffineShadow[1].pd = 0x100;
    gBgAffineShadow[1].x = 0;
    gBgAffineShadow[1].y = 0;
    gAfterVBlankByte = 0;
    gInitHalf03002CB4 = 0;
    gInitHalf03002B50 = 0x100;
    gInitHalf03006C24 = 0x100;
    gInitHalf03003F18 = 0;
    gInitHalf030065E4 = 0;
    gInitHalf03002CBC = 0;
    gInitHalf03003BEC = 0;
    gInitHalf03006C28 = 0x100;
    gWindowShadow[0] = 0;
    gWindowShadow[1] = 0;
    gWindowShadow[2] = 0;
    gWindowShadow[3] = 0;
    gWindowShadow[4] = 0;
    gWindowShadow[5] = 0;
    gBlendShadow[0] = 0;
    gBlendShadow[1] = 0;
    gBlendShadow[2] = 0;
    gInitWord03006C50 = 0;
    for (i = 0; i < 10; i++)
    {
        gKeyInitialDelays[i] = 20;
        gKeyRepeatDelays[i] = 8;
    }
    gInputConfig[8] = 0;
    gRawHeldKeys = 0;
    gInitWord03006C48 = 0;
    gInitWord030030D4 = 0;
    for (i = 0; i < 15; i++)
        gIrqHandlers[i] = gIrqDefaultHandlers[i];

    FILL32(0, gScanlineBufferA, 0x85000140);
    gScanlineWriteBuffer = gScanlineBufferA;
    gScanlineReadBuffer = gScanlineBufferA + 0x280;
    gScanlineDmaDestination = 0;
    gScanlineByte02000518 = 0;
    gGraphicsByte03002BF0 = 0;
    gGraphicsByte03002C54 = 0;
    FILL32(0, &gGraphicsByte03003B30, 0x85000004);
    FILL32(0, &gGraphicsByte03003F80, 0x85000004);
    gGraphicsByte030065E0 = 0;
    gGraphicsByte03002CB8 = 0;
    FILL32(0, &gGraphicsByte03002BD0, 0x85000006);
    FILL32(0, gGraphicsFrameCallbacks, 0x85000006);
    Func_0810AD34();
    Func_0810B2D0(0x0095FC00);
    Func_0810ADAC();
    gFrameBeginByte = 1;
    Tasks_Initialize();
    Func_08115618();
    gGameHalf03002BEC = 0x1F0;
    gGamePointer03002CB0 = (void *)0x06014200;
    Func_08113C38();
    if (Func_081156FC(4) != 0)
        gSystemFlags |= 0x100;

    DMA_START(0x080000FC, gIrqMainBuffer, 0x84000080);
    DMA_WAIT();
    IO32(0x03007FFC) = (DbaaU32)gIrqMainBuffer;
    IO16(0x04000200) = 1;
    IO16(0x04000004) = 0x18;
    IO16(0x04000208) = 1;
    FILL32(0, gInputBufferA, 0x85000005);
    FILL32(0, gInputBufferB, 0x85000014);
    gInputResult = 0;
    gInputMode = 0;
    Func_08113CE0(0);
    gInitByte030065EC = 0;
    gInitWord03002C50 = 0;
    gInitByte03002CC0 = 0;
}
