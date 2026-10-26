#include "runtime.h"

/* USA 0x0800152C. Startup trampoline; the permanent loop is entered later. */
void Game_Entry(void)
{
    Game_Bootstrap();
}
