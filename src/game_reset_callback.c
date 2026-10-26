#include "runtime.h"

/* USA 0x08001440, registered as a callback by Game_CreateCounterTask. */
void Game_ResetVideoStateCallback(void)
{
    Game_ResetVideoState();
}
