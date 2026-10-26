#include "runtime.h"

extern DbaaU16 gGameHalf03002BEC;
extern void *gGamePointer03002CB0;
extern DbaaU32 gGameWord02029770;
extern DbaaU8 gGameData020298C0[];
extern DbaaU8 gGameBytes02029FC8[];
void Func_08113C38(void);
void Func_080043F4(void);
void Func_080A30F8(void);
void Func_08102BF4(void);
void Func_0800C364(void);
void Func_080A38CC(void);
void Func_080FA048(void);
DbaaU8 Func_08001538(void);
void Func_08001D00(int mode);
void Func_080030A0(void);
void Func_08001BE4(void);
void Func_08002AA8(void);

int Game_Initialize(void)
{
    int result = 0;
    DbaaU16 fill;

    gGameHalf03002BEC = 0x200;
    gGamePointer03002CB0 = (void *)0x06014000;
    Func_08113C38();
    Func_080043F4();
    Func_080A30F8();
    gGameWord02029770 = 0;
    fill = 0;
    Bios_CpuSet(&fill, gGameData020298C0, 0x01000028);
    Func_08102BF4();
    Func_0800C364();
    Func_080A38CC();
    Func_080FA048();
    if ((gSystemFlags & 0x100) == 0)
    {
        if (Func_08001538() == 2)
        {
            Func_08001D00(2);
            Func_08001D00(1);
            Func_08001D00(0);
            result = 1;
        }
        else
        {
            Func_08001D00(2);
            Func_08001D00(1);
            Func_08001D00(0);
            Func_080030A0();
        }
        Func_08001BE4();
        gGameBytes02029FC8[0] = gDbaaGameState.byte02 & 1;
        gGameBytes02029FC8[1] = gGameBytes02029FC8[0];
        gGameBytes02029FC8[2] = gGameBytes02029FC8[0];
    }
    else
        Func_08002AA8();
    return result;
}
