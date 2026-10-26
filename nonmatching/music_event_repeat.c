#include "audio.h"
void MusicEvent_Goto(void *, DbaaU8 *);
void MusicEvent_Repeat(void *player, DbaaU8 *track) {
  const DbaaU8 *command = *(const DbaaU8 **)(track + 0x40);
  unsigned count = command[0];
  if (!count) {
    *(const DbaaU8 **)(track + 0x40) = command + 1;
    MusicEvent_Goto(player, track);
  } else {
    unsigned repeat = track[3] + 1;
    track[3] = repeat;
    command = *(const DbaaU8 **)(track + 0x40);
    *(const DbaaU8 **)(track + 0x40) = command + 1;
    count = *command;
    if ((DbaaU32)command < 0x02000000)
      count = 0;
    if (repeat < count)
      MusicEvent_Goto(player, track);
    else {
      track[3] = 0;
      *(const DbaaU8 **)(track + 0x40) = command + 5;
    }
  }
}
