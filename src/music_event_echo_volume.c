/* USA 0x0810C1E4: 12 complete linked bytes match; C/GNU C only. */
#include "audio.h"
void MusicEvent_EchoVolume(void *player, DbaaU8 *track) {
  track[0x1e] = **(const DbaaU8 **)(track + 0x40);
  (*(const DbaaU8 **)(track + 0x40))++;
}
