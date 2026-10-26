/* Readable behavioral reference only; excluded from byte matching. */
#include "audio.h"
void Cgb_UpdateVolume(DbaaU8 *channel) {
  DbaaU8 right = channel[2], left = channel[3];
  if (right >= left) {
    if ((right >> 1) >= left) {
      channel[0x1B] = 0x0F;
      goto limit_volume;
    }
  } else if ((left >> 1) >= right) {
    channel[0x1B] = 0xF0;
    goto limit_volume;
  }
  channel[0x1B] = 0xFF;
  channel[0x0A] = (channel[3] + channel[2]) >> 4;
  goto apply_volume;
limit_volume:
  {
    int value = (channel[3] + channel[2]) >> 4;
    channel[0x0A] = value;
    if (value > 15)
      channel[0x0A] = 15;
  }
apply_volume:
  channel[0x19] = (channel[6] * channel[0x0A] + 15) >> 4;
  channel[0x1B] = channel[0x1C] & channel[0x1B];
}
