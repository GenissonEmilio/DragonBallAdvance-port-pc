#include "audio_runtime.h"
#include "audio_helpers.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct DbaaAudioRuntime {
  DbaaMusicHost host;
  uint8_t *rom, ewram[0x40000], iwram[0x8000], io[1024];
  DbaaAudioStats stats;
  DbaaPcmBlock block;
  int16_t ring[DBAA_AUDIO_RING][2];
  size_t head, queued;
  uint64_t phase;
  unsigned gain;
  int initialized;
  DbaaBusObserver observer;
  void *observer_user;
  uint8_t clock_trace[1024];
  size_t clock_trace_count;
  char error[160];
};

static void fault(DbaaAudioRuntime *r, const char *message) {
  ++r->stats.faults;
  if (!r->error[0])
    snprintf(r->error, sizeof(r->error), "%s", message);
}

static uint8_t *region(DbaaAudioRuntime *r, uint32_t a, size_t n, int write) {
  if (a >= 0x02000000 && a < 0x02040000 && n <= 0x02040000u - a)
    return r->ewram + a - 0x02000000;
  if (a >= 0x03000000 && a < 0x03008000 && n <= 0x03008000u - a)
    return r->iwram + a - 0x03000000;
  if (a >= 0x04000000 && a < 0x04000400 && n <= 0x04000400u - a)
    return r->io + a - 0x04000000;
  if (!write && a >= 0x08000000 && a < 0x09000000 && n <= 0x09000000u - a)
    return r->rom + a - 0x08000000;
  fault(r, "unmapped memory or ROM write");
  return NULL;
}

static uint32_t peek(DbaaAudioRuntime *r, uint32_t a, uint32_t n) {
  uint8_t *p = region(r, a, n, 0);
  uint32_t v = 0;
  if (p)
    for (uint32_t i = 0; i < n; ++i)
      v |= (uint32_t)p[i] << (8 * i);
  return v;
}

static uint32_t host_read(void *user, uint32_t a, uint32_t n) {
  DbaaAudioRuntime *r = user;
  if (n != 1 && n != 2 && n != 4) {
    fault(r, "invalid read width");
    return 0;
  }
  if (a == 0x04000006) {
    unsigned line = (unsigned)(r->stats.cycles / DBAA_LINE_CYCLES % 228);
    r->io[6] = (uint8_t)line;
    if (r->clock_trace_count < sizeof(r->clock_trace))
      r->clock_trace[r->clock_trace_count++] = (uint8_t)line;
    /* A polled line wait advances the host's virtual scanline, not CPU cycles
     * per instruction. Frame deadlines use the exact GBA master-clock ratio. */
    r->stats.cycles += DBAA_LINE_CYCLES;
  }
  uint32_t value = peek(r, a, n);
  if (r->observer)
    r->observer(r->observer_user, 0, a, n, value);
  return value;
}

static void host_write(void *user, uint32_t a, uint32_t value, uint32_t n) {
  DbaaAudioRuntime *r = user;
  if (n != 1 && n != 2 && n != 4) {
    fault(r, "invalid write width");
    return;
  }
  uint8_t *p = region(r, a, n, 1);
  if (p)
    for (uint32_t i = 0; i < n; ++i)
      p[i] = (uint8_t)(value >> (8 * i));
  if (r->observer)
    r->observer(r->observer_user, 1, a, n,
                value & (n == 4 ? UINT32_MAX : (1u << (8 * n)) - 1));
}

static uint32_t host_call(void *user, uint32_t target, uint32_t a, uint32_t b,
                          uint32_t c) {
  DbaaAudioRuntime *r = user;
  (void)target;
  (void)a;
  (void)b;
  (void)c;
  fault(r, "unbound game routine; native audio never executes ARM");
  return 0;
}

static uint32_t crc32(const uint8_t *p, size_t n) {
  uint32_t crc = UINT32_MAX;
  for (size_t i = 0; i < n; ++i) {
    crc ^= p[i];
    for (unsigned bit = 0; bit < 8; ++bit)
      crc = (crc >> 1) ^ ((0u - (crc & 1u)) & 0xEDB88320u);
  }
  return ~crc;
}

DbaaAudioRuntime *Dbaa_AudioRuntimeCreate(const uint8_t *rom, size_t n) {
  if (!rom || n != 0x1000000 || crc32(rom, n) != 0x7D7306DFu)
    return NULL;
  DbaaAudioRuntime *r = calloc(1, sizeof(*r));
  if (!r)
    return NULL;
  r->rom = malloc(n);
  if (!r->rom) {
    free(r);
    return NULL;
  }
  memcpy(r->rom, rom, n);
  r->gain = 64; /* Application gain only; never modifies the original PCM. */
  r->host = (DbaaMusicHost){r, host_read, host_write, host_call};
  return r;
}

void Dbaa_AudioRuntimeDestroy(DbaaAudioRuntime *r) {
  if (r) {
    free(r->rom);
    free(r);
  }
}

int Dbaa_AudioRuntimeInitialize(DbaaAudioRuntime *r) {
  if (!r || r->stats.faults)
    return 0;
  r->clock_trace_count = 0;
  Dbaa_AudioInitialize(&r->host);
  r->phase = 0;
  r->head = r->queued = 0;
  r->initialized = 1;
  return r->stats.faults == 0;
}

void Dbaa_AudioVBlank(const DbaaMusicHost *h) {
#define R(a, n) h->read(h->user, (a), (n))
#define W(a, v, n) h->write(h->user, (a), (v), (n))
  uint32_t sound = R(0x03007FF0, 4);
  if (R(sound, 4) - 0x68736D53u > 1)
    return;
  int count = (int)R(sound + 4, 1) - 1;
  W(sound + 4, (uint32_t)count, 1);
  if (count > 0)
    return;
  W(sound + 4, R(sound + 11, 1), 1);
  if (R(0x040000C4, 4) & 0x02000000u)
    W(0x040000C4, 0x84400004u, 4);
  if (R(0x040000D0, 4) & 0x02000000u)
    W(0x040000D0, 0x84400004u, 4);
  W(0x040000C6, 0x400, 2);
  W(0x040000D2, 0x400, 2);
  W(0x040000C6, 0xB600, 2);
  W(0x040000D2, 0xB600, 2);
#undef R
#undef W
}

static int signed_byte(unsigned x) { return x < 128 ? (int)x : (int)x - 256; }

static int16_t output_sample(int value, unsigned gain) {
  /* Multiply first: gain 256 maps signed PCM8 to signed PCM16 exactly.
   * C99 division truncation is part of this host-only conversion policy. */
  int result = value * (int)gain / 2;
  return (int16_t)(result < -32768 ? -32768 : result > 32767 ? 32767 : result);
}

int Dbaa_AudioRuntimeFrame(DbaaAudioRuntime *r) {
  if (!r || !r->initialized || r->stats.faults)
    return 0;
  uint32_t sound = peek(r, 0x03007FF0, 4);
  uint32_t count = peek(r, sound + 16, 4), period = peek(r, sound + 11, 1);
  uint32_t ticks = 65536u - peek(r, 0x04000100, 2);
  if (!count || count > DBAA_PCM_MAX || period < 2 || count * period > 1584 ||
      count * ticks != DBAA_FRAME_CYCLES) {
    fault(r, "unsupported PCM frequency/period");
    return 0;
  }
  /* Reserve an entire frame atomically: never overwrite unread output. */
  size_t needed =
      (size_t)((r->phase + (uint64_t)DBAA_FRAME_CYCLES * DBAA_OUTPUT_HZ) /
               DBAA_CPU_HZ);
  if (needed > DBAA_AUDIO_RING - r->queued) {
    r->stats.overflow_samples += needed;
    fault(r, "audio ring overflow; consumer is not keeping up");
    return 0;
  }
  r->stats.cycles =
      (r->stats.cycles / DBAA_FRAME_CYCLES + 1) * DBAA_FRAME_CYCLES +
      160 * DBAA_LINE_CYCLES;
  Dbaa_AudioVBlank(&r->host);
  uint32_t counter = peek(r, sound + 4, 1);
  uint32_t lock = peek(r, sound, 4);
  int active = lock - 0x68736D53u <= 1;
  if (active && (!counter || counter > period)) {
    fault(r, "invalid PCM DMA counter");
    return 0;
  }
  uint32_t playing = active ? (period - counter) * count : 0;
  uint32_t produced =
      active && counter > 1 ? (period - (counter - 1)) * count : 0;
  Dbaa_AudioMain(&r->host);
  if (r->stats.faults)
    return 0;
  r->block.count = count;
  r->block.playing_offset = playing;
  r->block.produced_offset = produced;
  r->block.timer_ticks = ticks;
  uint32_t control = peek(r, 0x04000082, 2);
  int enabled = !!(peek(r, 0x04000084, 2) & 128);
  int timer = !!(peek(r, 0x04000102, 2) & 128);
  int dma_a = !!(peek(r, 0x040000C6, 2) & 0x8000);
  int dma_b = !!(peek(r, 0x040000D2, 2) & 0x8000);
  if (control & 0x4400) {
    fault(r, "Timer1 PCM is not supported by this audio backend");
    return 0;
  }
  uint32_t cgb = peek(r, sound + 28, 4);
  for (unsigned i = 0; i < 4; ++i)
    if (peek(r, cgb + i * 64, 1) & 0xC7) {
      ++r->stats.cgb_active_frames;
      break;
    }
  for (uint32_t i = 0; i < count; ++i) {
    unsigned a = peek(r, sound + 0x350 + playing + i, 1);
    unsigned b = peek(r, sound + 0x980 + playing + i, 1);
    r->block.right[i] = (uint8_t)a;
    r->block.left[i] = (uint8_t)b;
    r->block.produced_right[i] =
        (uint8_t)peek(r, sound + 0x350 + produced + i, 1);
    r->block.produced_left[i] =
        (uint8_t)peek(r, sound + 0x980 + produced + i, 1);
    int va = active && enabled && timer && dma_a ? signed_byte(a) : 0;
    int vb = active && enabled && timer && dma_b ? signed_byte(b) : 0;
    /* DirectSound A is right and B is left in the game's 0xA90E setup. */
    int left = ((control & 0x200) ? va * ((control & 4) ? 2 : 1) : 0) +
               ((control & 0x2000) ? vb * ((control & 8) ? 2 : 1) : 0);
    int right = ((control & 0x100) ? va * ((control & 4) ? 2 : 1) : 0) +
                ((control & 0x1000) ? vb * ((control & 8) ? 2 : 1) : 0);
    r->phase += (uint64_t)ticks * DBAA_OUTPUT_HZ;
    while (r->phase >= DBAA_CPU_HZ) {
      size_t tail = (r->head + r->queued) % DBAA_AUDIO_RING;
      r->ring[tail][0] = output_sample(left, r->gain);
      r->ring[tail][1] = output_sample(right, r->gain);
      ++r->queued;
      ++r->stats.converted_samples;
      r->phase -= DBAA_CPU_HZ;
    }
  }
  ++r->stats.frames;
  r->stats.source_samples += count;
  if (r->queued > r->stats.max_queued)
    r->stats.max_queued = r->queued;
  return 1;
}

size_t Dbaa_AudioRuntimeRead(DbaaAudioRuntime *r, int16_t *out, size_t n) {
  if (!r || !out)
    return 0;
  size_t actual = n < r->queued ? n : r->queued;
  for (size_t i = 0; i < actual; ++i) {
    out[2 * i] = r->ring[r->head][0];
    out[2 * i + 1] = r->ring[r->head][1];
    r->head = (r->head + 1) % DBAA_AUDIO_RING;
  }
  memset(out + 2 * actual, 0, (n - actual) * 2 * sizeof(*out));
  r->queued -= actual;
  r->stats.consumed_samples += actual;
  r->stats.underrun_samples += n - actual;
  return actual;
}

size_t Dbaa_AudioRuntimeQueued(const DbaaAudioRuntime *r) {
  return r ? r->queued : 0;
}
void Dbaa_AudioRuntimeStats(const DbaaAudioRuntime *r, DbaaAudioStats *s) {
  if (r && s)
    *s = r->stats;
}
void Dbaa_AudioRuntimeBlock(const DbaaAudioRuntime *r, DbaaPcmBlock *b) {
  if (r && b)
    *b = r->block;
}
void Dbaa_AudioRuntimeObserve(DbaaAudioRuntime *r, DbaaBusObserver fn,
                              void *u) {
  r->observer = fn;
  r->observer_user = u;
}
size_t Dbaa_AudioRuntimeClockTrace(const DbaaAudioRuntime *r, uint8_t *out,
                                   size_t n) {
  size_t length = r->clock_trace_count < n ? r->clock_trace_count : n;
  if (out)
    memcpy(out, r->clock_trace, length);
  return length;
}
int Dbaa_AudioRuntimeMemory(DbaaAudioRuntime *r, uint32_t a, void *data,
                            size_t n, int write) {
  uint8_t *p = region(r, a, n, write);
  if (!p || !data)
    return 0;
  if (write)
    memcpy(p, data, n);
  else
    memcpy(data, p, n);
  return 1;
}
const char *Dbaa_AudioRuntimeError(const DbaaAudioRuntime *r) {
  return r ? r->error : "null audio runtime";
}
void Dbaa_AudioRuntimeGain(DbaaAudioRuntime *r, unsigned gain) {
  r->gain = gain > 256 ? 256 : gain;
}
int Dbaa_AudioRuntimeMode(DbaaAudioRuntime *r, unsigned index) {
  if (!r || !r->initialized || index < 1 || index > 12)
    return 0;
  Dbaa_SoundMode(&r->host, index << 16);
  return !r->stats.faults;
}
int Dbaa_AudioRuntimeSuspend(DbaaAudioRuntime *r, int suspend) {
  if (!r || !r->initialized)
    return 0;
  if (suspend)
    Dbaa_SoundVSyncOff(&r->host);
  else
    Dbaa_SoundVSyncOn(&r->host);
  return !r->stats.faults;
}
int Dbaa_AudioRuntimeDemo(DbaaAudioRuntime *r) {
  if (!r || !r->initialized)
    return 0;
  /* Explicit synthetic fixture: a quiet looping triangle, not a game song. */
  uint32_t sound = peek(r, 0x03007FF0, 4), channel = sound + 0x50;
  uint32_t wave = 0x02010000;
  for (unsigned i = 0; i < 64; ++i)
    host_write(r, channel + i, 0, 1);
  host_write(r, channel, 0x11, 1);
  host_write(r, channel + 1, 8, 1);
  host_write(r, channel + 2, 192, 1);
  host_write(r, channel + 3, 128, 1);
  host_write(r, channel + 9, 255, 1);
  host_write(r, channel + 0x18, 64, 4);
  host_write(r, channel + 0x24, wave, 4);
  host_write(r, channel + 0x28, wave + 16, 4);
  host_write(r, wave + 3, 0xC0, 1);
  host_write(r, wave + 8, 0, 4);
  host_write(r, wave + 12, 64, 4);
  for (unsigned i = 0; i < 65; ++i) {
    unsigned x = i % 64;
    int sample = x < 32 ? (int)x - 16 : 48 - (int)x;
    host_write(r, wave + 16 + i, (uint32_t)sample, 1);
  }
  return !r->stats.faults;
}
int Dbaa_AudioRuntimeStartSong(DbaaAudioRuntime *r, unsigned song) {
  if (!r || !r->initialized || r->stats.faults || song >= DBAA_SONG_COUNT)
    return 0;
  Dbaa_MusicStartSong(&r->host, song);
  return !r->stats.faults;
}
int Dbaa_AudioRuntimeStopPlayer(DbaaAudioRuntime *r, unsigned player_index) {
  if (!r || !r->initialized || r->stats.faults || player_index >= 4)
    return 0;
  Dbaa_MusicPlayerStop(&r->host, peek(r, 0x08A69038u + player_index * 12u, 4));
  return !r->stats.faults;
}
int Dbaa_AudioRuntimeStopAll(DbaaAudioRuntime *r) {
  if (!r || !r->initialized || r->stats.faults)
    return 0;
  Dbaa_MusicStopAll(&r->host);
  return !r->stats.faults;
}
uint64_t Dbaa_AudioDeadline(uint64_t frame, uint64_t frequency) {
  /* Split before multiplying, avoiding accumulated truncation and overflow. */
  if (!frequency || frequency > UINT32_MAX ||
      frame > UINT64_MAX / DBAA_FRAME_CYCLES)
    return UINT64_MAX;
  uint64_t cycles = frame * DBAA_FRAME_CYCLES;
  if (cycles / DBAA_CPU_HZ > (UINT64_MAX - UINT32_MAX) / frequency)
    return UINT64_MAX;
  return cycles / DBAA_CPU_HZ * frequency +
         (cycles % DBAA_CPU_HZ) * frequency / DBAA_CPU_HZ;
}
