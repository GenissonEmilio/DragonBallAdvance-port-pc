#include "runtime.h"
#include "input.h"

/* USA 0x0810D2F8: sample ten GBA keys, edge masks and per-key repeat counters. */
void Input_Update(void)
{
    DbaaU8 *timers = gKeyRepeatTimers;
    DbaaU8 *initialDelays = gKeyInitialDelays;
    DbaaU8 *repeatDelays = gKeyRepeatDelays;
    DbaaS8 i;

    gHeldKeys = ~REG_KEYINPUT & 0x3FF;
    gRawHeldKeys = gHeldKeys;
    if (gInputConfig[8] == 1)
        Func_0811456C(gHeldKeys);
    else if (gInputConfig[8] == 2)
        gHeldKeys = Func_0811453C();

    gPressedKeys = (gHeldKeys ^ gPreviousKeys) & gHeldKeys;
    gReleasedKeys = (gHeldKeys ^ gPreviousKeys) & gPreviousKeys;
    gPreviousKeys = gHeldKeys;
    gRepeatKeys = gPressedKeys;

    for (i = 0; i < 10; i++)
    {
        if (((gHeldKeys >> i) & 1) == 0)
            timers[i] = initialDelays[i];
        else if (timers[i] != 0)
            timers[i]--;
        else
        {
            gRepeatKeys |= 1 << i;
            timers[i] = repeatDelays[i];
        }
    }
}
