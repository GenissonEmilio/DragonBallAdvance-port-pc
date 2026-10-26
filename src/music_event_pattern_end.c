/* USA 0x0810A590: all 20 linked bytes match; only empty GNU C constraints. */
#include "audio.h"
void MusicEvent_PatternEnd(void *player, DbaaU8 *input) {
  register DbaaU8 *track __asm__("r1") = input;
  register DbaaU32 depth __asm__("r2");
  register DbaaU8 *slot __asm__("r3");
  __asm__("" : "+r"(track));
  depth = track[2];
  __asm__("" : "+r"(depth));
  if (depth) {
    depth--;
    track[2] = depth;
    depth <<= 2;
    slot = track + depth;
    __asm__("" : "+r"(slot));
    depth = *(DbaaU32 *)(slot + 0x44);
    *(DbaaU32 *)(track + 0x40) = depth;
  }
}
