#ifndef DBAA_DIGITAL_MIXER_H
#define DBAA_DIGITAL_MIXER_H
#include <stdint.h>
typedef struct {
  int16_t left, right;
  uint8_t dac_clipped, pcm_clipped;
} DbaaDigitalSample;
/* Native digital GBA routing/bias/saturation, before analog filtering/PWM.
 * gain 256 maps a full-volume DirectSound PCM8 source to PCM8*256. */
int Dbaa_DigitalMix(int16_t psg_left, int16_t psg_right,
                    int8_t pcm_a, int8_t pcm_b, uint16_t control,
                    uint16_t bias, unsigned gain, DbaaDigitalSample *result);
#endif
