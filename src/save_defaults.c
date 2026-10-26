#include "save_services.h"

void Func_08002AA8(void)
{
    DbaaU8 i;

    gSaveGameState.byte04 = 0x12;
    gSaveGameState.byte05 = 0x11;
    gSaveGameState.byte06 = 2;
    gSaveGameState.byte24 = 0xff;
    gSaveGameState.byte02 = 1;
    {
        /* Empty GNU C constraint; the compiler still emits every instruction. */
        register DbaaU32 value __asm__("r2") = 0x23;
        __asm__("" : : "r"(value));
        gSaveGameState.byte38 = value;
    }
    gSaveGameState.half3A = 0x400;
    gSaveGameState.word3C = -1;
    for (i = 0; i < 7; i++)
        gSaveGameState.bits25[i] |= 0xff;
    {
        /* Preserve the original shift and narrowing instead of constant folding. */
        int indexBase = 0x30;
        __asm__("" : "+r"(indexBase));
        gSaveGameState.bits25[(DbaaU8)(indexBase >> 3)] |= 0x40;
    }
    Func_08002940();
    gSaveGameState.checksum = Func_08002DA8(&gSaveGameState);
}
