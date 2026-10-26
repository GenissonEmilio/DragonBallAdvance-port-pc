/* Reference only: call mGBA's original GBAAudioSample mixing/bias path.
 * The synthetic channel amplitudes represent legitimate digital PSG outputs.
 * No ROM or CPU executes, and this file is never linked into the port. */
#include <mgba/internal/gb/audio.h>
#include <mgba/internal/gba/audio.h>
#include <mgba/internal/gba/gba.h>
#include <stdlib.h>

typedef struct {
  struct GBA board;
  int32_t relative, next;
} MixOracle;

__declspec(dllexport) MixOracle *Ref_MixCreate(void) {
  MixOracle *p = calloc(1, sizeof(*p));
  if (!p)
    return NULL;
  mTimingInit(&p->board.timing, &p->relative, &p->next);
  p->board.audio.p = &p->board;
  GBAAudioInit(&p->board.audio, 1024);
  GBAAudioReset(&p->board.audio);
  return p;
}
__declspec(dllexport) void Ref_MixDestroy(MixOracle *p) {
  if (!p)
    return;
  GBAAudioDeinit(&p->board.audio);
  mTimingDeinit(&p->board.timing);
  free(p);
}
__declspec(dllexport) void Ref_MixSample(MixOracle *p, const uint8_t *channels,
                                         uint16_t low_control, int8_t a,
                                         int8_t b, uint16_t high_control,
                                         uint16_t bias, int16_t *output) {
  struct GBAAudio *audio = &p->board.audio;
  GBAudioWriteNR50(&audio->psg, (uint8_t)low_control);
  GBAudioWriteNR51(&audio->psg, (uint8_t)(low_control >> 8));
  audio->psg.ch1.sample = channels[0];
  audio->psg.ch2.sample = channels[1];
  audio->psg.ch3.sample = channels[2];
  audio->psg.ch4.sample = channels[3];
  GBAudioSamplePSG(&audio->psg, &output[0], &output[1]);
  GBAAudioWriteSOUNDCNT_HI(audio, high_control);
  audio->chA.samples[0] = a;
  audio->chB.samples[0] = b;
  audio->soundbias = bias & 0x3FE;
  audio->lastSample = 0;
  audio->sampleIndex = 0;
  GBAAudioSample(audio, audio->sampleInterval);
  output[2] = audio->currentSamples[0].left;
  output[3] = audio->currentSamples[0].right;
}
