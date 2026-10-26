/* Hardware reference only: full pinned mGBA GBA I/O/audio scheduler. This
 * library is never linked by the native port. No ROM or CPU executes here. */
#include <mgba-util/audio-buffer.h>
#include <mgba/internal/gb/audio.h>
#include <mgba/internal/gba/audio.h>
#include <mgba/internal/gba/gba.h>
#include <mgba/internal/gba/io.h>
#include <stdlib.h>

typedef struct {
  struct GBA board;
  int32_t relative, next;
  uint64_t cycles;
} ReferencePsg;

__declspec(dllexport) ReferencePsg *Ref_PsgCreate(void) {
  ReferencePsg *p = calloc(1, sizeof(*p));
  if (!p)
    return NULL;
  mTimingInit(&p->board.timing, &p->relative, &p->next);
  p->board.audio.p = &p->board;
  GBAAudioInit(&p->board.audio, 1024);
  GBAAudioReset(&p->board.audio);
  mTimingTick(&p->board.timing, 0);
  return p;
}
__declspec(dllexport) void Ref_PsgDestroy(ReferencePsg *p) {
  if (p) {
    GBAAudioDeinit(&p->board.audio);
    mTimingDeinit(&p->board.timing);
    free(p);
  }
}
__declspec(dllexport) int Ref_PsgAdvance(ReferencePsg *p, uint64_t target) {
  if (!p || target < p->cycles)
    return 0;
  /* Dispatch each original event at its own timestamp rather than batching
   * late events: the PSG frame sequencer must see the exact cycle. */
  while (p->cycles < target) {
    int32_t delta = mTimingNextEvent(&p->board.timing);
    uint64_t left = target - p->cycles;
    if (delta < 0)
      return 0;
    if ((uint64_t)delta > left)
      delta = (int32_t)left;
    mTimingTick(&p->board.timing, delta);
    p->cycles += (uint32_t)delta;
    mAudioBufferClear(&p->board.audio.psg.buffer);
  }
  return 1;
}
__declspec(dllexport) int Ref_PsgWrite(ReferencePsg *p, uint64_t cycles,
                                       uint32_t address, uint32_t value,
                                       unsigned width) {
  if (!Ref_PsgAdvance(p, cycles))
    return 0;
  address -= 0x04000000;
  if (width == 1)
    GBAIOWrite8(&p->board, address, value);
  else if (width == 2)
    GBAIOWrite(&p->board, address, value);
  else if (width == 4)
    GBAIOWrite32(&p->board, address, value);
  else
    return 0;
  return 1;
}
__declspec(dllexport) uint8_t Ref_PsgStatus(ReferencePsg *p) {
  return p->board.memory.io[0x84 >> 1];
}
__declspec(dllexport) void Ref_PsgSample(ReferencePsg *p, int16_t *left,
                                         int16_t *right) {
  GBAudioSamplePSG(&p->board.audio.psg, left, right);
}
