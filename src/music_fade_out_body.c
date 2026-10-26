/* USA 0x0810B610: 200 complete bytes match the ROM.
 * GNU C register-flow reconstruction; all instruction selection is performed
 * by the unmodified compiler. Empty constraints emit no instructions.
 */
#include "audio.h"
void Music_FadeOutBody(struct MusicPlayer *input) {
  register DbaaU32 a __asm__("r0"), b __asm__("r1"), c __asm__("r2"),
      d __asm__("r3");
  register struct MusicTrack *track __asm__("r4");
  register int count __asm__("r5");
  register struct MusicPlayer *player __asm__("r6") = input;
  register DbaaU32 level;
  b = player->fadeInterval;
  if (!b)
    return;
  a = player->fadeCounter;
  a--;
  player->fadeCounter = a;
  d = 0xFFFF;
  __asm__("" : "+r"(d));
  c = d;
  a <<= 16;
  d = a >> 16;
  if (d)
    return;
  player->fadeCounter = b;
  b = player->fadeLevel;
  a = 2;
  a &= b;
  if (!a)
    goto fade_out;
  a = b;
  a += 16;
  player->fadeLevel = a;
  a &= c;
  if (a > 255) {
    a = 256;
    player->fadeLevel = a;
    player->fadeInterval = d;
  }
  goto apply_volume;
fade_out:
  a = b;
  a -= 16;
  player->fadeLevel = a;
  a &= c;
  a <<= 16;
  if ((int)a > 0)
    goto apply_volume;
  count = player->trackCount;
  track = player->tracks;
  while (count > 0) {
    MusicTrack_Stop(player, track);
    a = 1;
    level = player->fadeLevel;
    a &= level;
    if (!a)
      track->status = a;
    count--;
    track++;
  }
  a = 1;
  b = player->fadeLevel;
  a &= b;
  if (a) {
    a = player->status;
    b = 0x80000000;
    a |= b;
  } else
    a = 0x80000000;
  player->status = a;
  a = 0;
  player->fadeInterval = a;
  return;
apply_volume:
  count = player->trackCount;
  track = player->tracks;
  if (count <= 0)
    return;
  d = 0x80;
  level = 0;
  c = 3;
  do {
    b = track->status;
    a = d;
    a &= b;
    if (a) {
      level = player->fadeLevel;
      a = level >> 2;
      track->volumePublic = a;
      a = b;
      a |= c;
      track->status = a;
    }
    count--;
    track++;
  } while (count > 0);
  __asm__("" : : "l"(level));
}
