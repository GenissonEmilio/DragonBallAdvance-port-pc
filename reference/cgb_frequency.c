/* Readable behavioral reference only; excluded from byte matching. */
#include "audio.h"
extern const DbaaU8 gCgbNoiseFrequencies[], gCgbKeyMap[];
extern const DbaaS16 gCgbPeriods[];
int Cgb_CalculateFrequency(DbaaU8 channel, DbaaU8 key, DbaaU8 fine) {
  int encoded, base, next;
  if (channel == 4) {
    if (key <= 20)
      key = 0;
    else {
      key -= 21;
      if (key > 59)
        key = 59;
    }
    return gCgbNoiseFrequencies[key];
  }
  if (key <= 35) {
    fine = 0;
    key = 0;
  } else {
    key -= 36;
    if (key > 130) {
      key = 130;
      fine = 255;
    }
  }
  encoded = gCgbKeyMap[key];
  base = gCgbPeriods[encoded & 15] >> (encoded >> 4);
  encoded = gCgbKeyMap[key + 1];
  next = gCgbPeriods[encoded & 15] >> (encoded >> 4);
  return base + (((next - base) * fine) >> 8) + 2048;
}
