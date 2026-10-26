#include "runtime.h"

/* USA 0x0810C90C. The permanent frame loop entered after Game_Entry.
 * Bits and auxiliary byte meanings remain provisional; the access order is retained.
 */
void Runtime_MainLoop(void)
{
    for (;;)
    {
        gFrameBeginByte = 0;
        if (gSystemFlags & 0x40000)
            Func_0810D3E8();

        if (gFrameMode == 0xFF)
        {
            Input_Update();
            if (gInputMode != 0)
            {
                Func_08000354();
                gInputResult = Func_08113DD4(gInputBufferA, gInputBufferB, 0);
                if (Func_08000440() == 0)
                    Func_0800113C();
            }
            else if ((gSystemFlags & 0x90000) == 0x80000)
            {
                Func_0811545C();
            }

            if ((gVideoWords[4] & 4) == 0)
                Tasks_RunFrame();
            else
                gFrameMode = 0;
        }

        gPreviousSystemFlags = gSystemFlags;
        Bios_VBlankIntrWait();
        gAfterVBlankByte = 0;

        if (gSystemFlags & 0x4000)
        {
            Graphics_CommitCpu();
            if ((gSystemFlags & 0x400) == 0)
                Graphics_ClearOamCpu();
        }
        else
        {
            Graphics_CommitDma();
            if ((gSystemFlags & 0x400) == 0)
                Graphics_ClearOamDma();
        }

        if (gSystemFlags & 0x400)
            gSystemFlags |= 0x800;
        else
            gSystemFlags &= ~0x800;

        if ((gSystemFlags & 0x4000) == 0)
            Func_0810ADAC();

        while (REG_DISPSTAT & 1)
            ;
    }
}
