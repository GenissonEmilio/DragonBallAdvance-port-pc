#include "digital_mixer.h"

static int16_t convert(int mix, int bias, unsigned gain, uint8_t *dac_clipped,
                       uint8_t *pcm_clipped) {
  int dac = mix + bias;
  if (dac < 0) {
    dac = 0;
    *dac_clipped = 1;
  }
  if (dac > 1023) {
    dac = 1023;
    *dac_clipped = 1;
  }
  int value = (dac - bias) * (int)gain / 4;
  if (value < -32768) {
    value = -32768;
    *pcm_clipped = 1;
  }
  if (value > 32767) {
    value = 32767;
    *pcm_clipped = 1;
  }
  return (int16_t)value;
}
int Dbaa_DigitalMix(int16_t psg_left, int16_t psg_right, int8_t pcm_a,
                    int8_t pcm_b, uint16_t control, uint16_t bias,
                    unsigned gain, DbaaDigitalSample *result) {
  if (!result || gain > 256)
    return 0;
  int a = (int)pcm_a * ((control & 4) ? 4 : 2);
  int b = (int)pcm_b * ((control & 8) ? 4 : 2);
  int left = (int)psg_left >> (4 - (control & 3));
  int right = (int)psg_right >> (4 - (control & 3));
  if (control & 0x200)
    left += a;
  if (control & 0x2000)
    left += b;
  if (control & 0x100)
    right += a;
  if (control & 0x1000)
    right += b;
  result->dac_clipped = result->pcm_clipped = 0;
  result->left = convert(left, bias & 0x3FE, gain, &result->dac_clipped,
                         &result->pcm_clipped);
  result->right = convert(right, bias & 0x3FE, gain, &result->dac_clipped,
                          &result->pcm_clipped);
  return 1;
}
