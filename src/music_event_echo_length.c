/* USA 0x0810C1F0: 12 complete linked bytes match; C/GNU C only. */
#include "audio.h"
void MusicEvent_EchoLength(void *player, DbaaU8 *track) {
  track[0x1f] = **(const DbaaU8 **)(track + 0x40);
  (*(const DbaaU8 **)(track + 0x40))++;
}
