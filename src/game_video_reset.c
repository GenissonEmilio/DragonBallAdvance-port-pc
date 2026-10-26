#include "runtime.h"

/* USA 0x080014D0: reset display shadow/data pointers and clear VRAM/palette RAM. */
void Game_ResetVideoState(void)
{
    DbaaU32 vramFill;
    DbaaU32 paletteFill;

    gDisplayControlShadow = 0x1140;
    gUnknownData03003BE4 = (const void *)0x0811855C;
    gUnknownData030030D0 = (const void *)0x0882323C;
    vramFill = 0;
    Bios_CpuSet(&vramFill, (void *)0x06000000, 0x05006000);
    paletteFill = 0;
    Bios_CpuSet(&paletteFill, (void *)0x05000000, 0x05000100);
}
