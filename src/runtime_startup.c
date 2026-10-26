#include "runtime.h"

/* USA 0x0810D65C, entered from ARM reset via the Thumb address 0x0810D65D. */
void Runtime_Startup(void)
{
    Runtime_Initialize();
    Game_Entry();
    Runtime_MainLoop();
}
