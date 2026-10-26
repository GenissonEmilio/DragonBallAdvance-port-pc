#include "game_state.h"

/* USA 0x0800144C: increment the 32-bit field when the byte flag is nonzero.
 * The unsigned type preserves the original modulo-2^32 addition.
 */
void State_IncrementWord10IfFlag22(void)
{
    if (gDbaaGameState.flag22 != 0)
        gDbaaGameState.word10++;
}
