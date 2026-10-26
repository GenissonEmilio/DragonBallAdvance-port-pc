#include "runtime.h"

/* USA 0x08001424: initialize game services and create the counter task. */
void Game_Bootstrap(void)
{
    Game_ResetVideoState();
    Game_Initialize();
    gDbaaGameState.byte08 = 2;
    Game_CreateCounterTask();
}
