/* USA 0x0810B6D8: 180 complete bytes match the ROM.
 * GNU C register-flow reconstruction; all instruction selection is performed
 * by the unmodified compiler. Empty constraints emit no instructions.
 */
#include "audio.h"
void MusicTrack_UpdateVolumePitch(struct MusicPlayer *player,
                                  struct MusicTrack *input) {
  register DbaaU32 a __asm__("r0"), b __asm__("r1"), c __asm__("r3"),
      d __asm__("r4");
  register struct MusicTrack *track __asm__("r2") = input;
  __asm__("" : "+r"(track));
  a = 1;
  b = track->status;
  a &= b;
  if (!a)
    goto pitch;
  c = track->volumePublic;
  __asm__("" : "+r"(c));
  b = track->volume;
  a = c;
  a *= b;
  c = a >> 5;
  d = track->modType;
  if (d != 1)
    goto pan;
  a = track->modulation;
  a += 128;
  a *= c;
  c = a >> 7;
pan:
  a = track->pan;
  a <<= 1;
  b = track->panPublic;
  b = a + b;
  if (d == 2) {
    a = track->modulation;
    b += a;
  }
  a = -128;
  if ((int)b < (int)a) {
    b = a;
    goto write_volume;
  }
  if ((int)b > 127)
    b = 127;
write_volume:
  a = b;
  a += 128;
  a *= c;
  a >>= 8;
  track->right = a;
  a = 127;
  a -= b;
  a *= c;
  a >>= 8;
  track->left = a;
pitch:
  b = track->status;
  a = 4;
  a &= b;
  c = b;
  if (!a)
    goto clear_flags;
  a = track->bend;
  b = track->bendRange;
  a *= b;
  b = track->tune;
  b += a;
  b <<= 2;
  a = track->keyShift;
  a <<= 8;
  b += a;
  a = track->keyShiftPublic;
  a <<= 8;
  b += a;
  a = track->pitchPublic;
  b = a + b;
  a = track->modType;
  if (!a) {
    a = track->modulation;
    a <<= 4;
    b += a;
  }
  a = (int)b >> 8;
  track->calculatedKey = a;
  track->calculatedPitch = b;
clear_flags:
  a = 0xFA;
  a &= c;
  track->status = a;
}
