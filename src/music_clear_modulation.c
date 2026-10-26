/* USA 0x0810AC40: all 28 linked bytes match; only empty constraints. */
#include "audio.h"
void Music_ClearModulation(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register DbaaU32 flags __asm__("r2"), status __asm__("r3");
  __asm__("" : "+r"(track));
  flags = 0;
  __asm__("" : "+r"(flags));
  track[0x16] = flags;
  track[0x1A] = flags;
  flags = track[0x18];
  __asm__("" : "+r"(flags));
  if (!flags)
    flags = 12;
  else
    flags = 3;
  __asm__("" : "+r"(flags));
  status = track[0];
  status |= flags;
  track[0] = status;
}
