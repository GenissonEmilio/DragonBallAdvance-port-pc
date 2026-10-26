/* USA 0x0810B884: 104 complete bytes match the ROM. */
#include "audio.h"
#define IN_REGISTER(reg, expression)                                           \
  ({                                                                           \
    register DbaaU32 dbaaRegisterValue __asm__(reg) = (DbaaU32)(expression);   \
    __asm__("" : "+r"(dbaaRegisterValue));                                     \
    dbaaRegisterValue;                                                         \
  })
void Cgb_UpdateVolume(DbaaU8 *data) {
  register DbaaU8 *channel __asm__("r1") = data;
  DbaaU32 rightBits;
  DbaaU32 right, leftByte, leftBits, left;
  __asm__("" : "+r"(channel));
  rightBits = IN_REGISTER("r2", IN_REGISTER("r0", channel[2]) << 24);
  right = IN_REGISTER("r4", rightBits >> 24);
  leftByte = IN_REGISTER("r3", channel[3]);
  leftBits = IN_REGISTER("r0", leftByte << 24);
  left = IN_REGISTER("r3", leftBits >> 24);
  if (right >= left) {
    if ((rightBits >> 25) >= left) {
      channel[0x1B] = 0x0F;
      goto limit_volume;
    }
  } else if ((leftBits >> 25) >= right) {
    channel[0x1B] = 0xF0;
    goto limit_volume;
  }
  /* Balanced stereo keeps the full sum; only directional paths clamp to 15. */
  channel[0x1B] = 0xFF;
  channel[0x0A] = IN_REGISTER("r0", IN_REGISTER("r2", channel[3]) +
                                        IN_REGISTER("r3", channel[2])) >>
                  4;
  goto apply_volume;
limit_volume:
  {
    DbaaU32 value = IN_REGISTER("r0", IN_REGISTER("r2", channel[3]) +
                                          IN_REGISTER("r3", channel[2])) >>
                    4;
    channel[0x0A] = value;
    if (value > 15)
      channel[0x0A] = 15;
  }
apply_volume:
  {
    int sustain = IN_REGISTER("r2", channel[6]);
    int volume = IN_REGISTER("r3", channel[0x0A]);
    channel[0x19] = ((int)IN_REGISTER("r0", sustain) * volume + 15) >> 4;
  }
  channel[0x1B] = IN_REGISTER("r0", IN_REGISTER("r0", channel[0x1C]) &
                                        IN_REGISTER("r2", channel[0x1B]));
  __asm__("" : : "r"(channel));
}
