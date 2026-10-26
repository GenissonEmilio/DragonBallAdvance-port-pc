/* USA 0x0810AC90: all 100 linked bytes match the ROM.
 * PCM note interpolation; Audio_MultiplyHigh retains product bits 63..32. */
#include "audio.h"
struct WaveFrequency {
  DbaaU32 type, frequency;
};
extern const DbaaU8 gMusicKeyMap[];
extern const DbaaU32 gMusicFrequencies[];
extern DbaaU32 Audio_MultiplyHigh(DbaaU32, DbaaU32);
DbaaU32 Music_CalculateFrequency(const struct WaveFrequency *wave, DbaaU8 key,
                                 DbaaU8 fine) {
  DbaaU32 first, second;
  DbaaU32 fraction = (DbaaU32)fine << 24;
  if (key > 178) {
    key = 178;
    fraction = 255u << 24;
  }
  first = gMusicKeyMap[key];
  first = gMusicFrequencies[first & 15] >> (first >> 4);
  second = gMusicKeyMap[key + 1];
  second = gMusicFrequencies[second & 15] >> (second >> 4);
  return Audio_MultiplyHigh(
      wave->frequency, first + Audio_MultiplyHigh(second - first, fraction));
}
