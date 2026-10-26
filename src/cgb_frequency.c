/* USA 0x0810B78C: 168 complete bytes match the ROM. */
#include "audio.h"
extern const DbaaU8 gCgbNoiseFrequencies[], gCgbKeyMap[];
extern const DbaaS16 gCgbPeriods[];
/* Empty constraints preserve signed arithmetic and original register lifetimes.
 */
#define IN_REGISTER(reg, expression)                                           \
  ({                                                                           \
    register int dbaaRegisterValue __asm__(reg) = (int)(expression);           \
    __asm__("" : "+r"(dbaaRegisterValue));                                     \
    dbaaRegisterValue;                                                         \
  })
int Cgb_CalculateFrequency(DbaaU8 channel, DbaaU8 key, DbaaU8 subkey) {
  register int fine __asm__("r12") = subkey;
  __asm__("" : "+r"(fine));
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
  {
    register const DbaaU8 *map __asm__("r3") = gCgbKeyMap;
    register const DbaaS16 *periods __asm__("r4");
    register int first __asm__("r6");
    register int mask __asm__("r2");
    register int base __asm__("r6");
    register int second __asm__("r1");
    int value;
    __asm__("" : "+r"(map));
    first = *(const DbaaU8 *)((DbaaU32)key + (DbaaU32)map);
    __asm__("" : "+r"(first));
    periods = gCgbPeriods;
    __asm__("" : "+r"(periods));
    mask = 15;
    __asm__("" : "+r"(mask));
    value = IN_REGISTER("r1", periods[first & mask]);
    base = value >> IN_REGISTER("r0", first >> 4);
    __asm__("" : "+r"(base));
    second = *(const DbaaU8 *)(IN_REGISTER("r0", key + 1) + (DbaaU32)map);
    __asm__("" : "+r"(second));
    value = IN_REGISTER("r0", periods[second & mask]);
    value >>= IN_REGISTER("r1", second >> 4);
    value = IN_REGISTER("r0", value - base);
    {
      register int product __asm__("r7") = IN_REGISTER("r7", fine);
      product *= value;
      __asm__("" : "+r"(product));
      return base + (IN_REGISTER("r0", product) >> 8) + 2048;
    }
  }
}
