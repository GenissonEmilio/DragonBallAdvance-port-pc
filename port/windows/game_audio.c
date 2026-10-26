/* Audio consumer for the statically translated game. It reads the original
 * driver's PCM buffers and clocks the standalone PSG. Guest CPU execution is
 * provided by generated/native C, never by this component. The digital output
 * policy is PCM16/48k, gain 64, sample hold; it does not model the analog DAC.
 */
#include "game_audio.h"
#include "audio_runtime.h"
#include "digital_mixer.h"
#include "psg.h"
#include "wasapi_sink.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *ewram, *iwram, *io_regs;
void Dbaa_GameAudioBindMemory(uint8_t *external, uint8_t *internal,
                              uint8_t *io) {
  ewram = external;
  iwram = internal;
  io_regs = io;
}

static struct {
  DbaaPsg *psg;
  FILE *pcm;
  int initialized, device, closed;
  const char *error;
  uint64_t cycles, samples, hash, cgb_samples, clipped, pcm_vblanks;
  uint64_t block_cycle, psg_nonzero, pcm_nonzero, dac_clipped;
  uint32_t right_base, left_base, block_offset, buffer_count, ticks;
  int pcm_active;
  int16_t staging[1024][2];
  size_t staged;
  DbaaWasapiStats device_stats;
} audio;

static uint32_t peek(uint32_t a, unsigned n) {
  const uint8_t *memory = NULL;
  uint32_t offset = 0, size = 0;
  switch (a >> 24) {
  case 2:
    memory = ewram;
    offset = a - 0x02000000u;
    size = 0x40000;
    break;
  case 3:
    memory = iwram;
    offset = a - 0x03000000u;
    size = 0x8000;
    break;
  case 4:
    memory = io_regs;
    offset = a - 0x04000000u;
    size = 0x400;
    break;
  default:
    return 0;
  }
  if (!memory || n > size || offset > size - n)
    return 0;
  uint32_t value = 0;
  for (unsigned i = 0; i < n; ++i)
    value |= (uint32_t)memory[offset + i] << (8 * i);
  return value;
}
static int fail(const char *reason) {
  if (!audio.error)
    audio.error = reason;
  return 0;
}
static int flush(void) {
  if (!audio.staged)
    return 1;
  const size_t frames = audio.staged;
  /* A partial device submission is fatal. Never retry that same block during
   * atexit, which would duplicate its already accepted prefix and capture. */
  audio.staged = 0;
  if (audio.pcm && fwrite(audio.staging, 4, frames, audio.pcm) != frames)
    return fail("cannot write game PCM capture");
  const uint8_t *bytes = (const uint8_t *)audio.staging;
  for (size_t i = 0; i < frames * 4; ++i) {
    audio.hash ^= bytes[i];
    audio.hash *= UINT64_C(1099511628211);
  }
  if (audio.device && !Dbaa_WasapiPush(&audio.staging[0][0], frames))
    return fail("WASAPI render worker stopped");
  return 1;
}
static uint64_t output_cycle(uint64_t sample) {
  return (sample / DBAA_OUTPUT_HZ) * DBAA_CPU_HZ +
         ((sample % DBAA_OUTPUT_HZ) * DBAA_CPU_HZ + DBAA_OUTPUT_HZ - 1) /
             DBAA_OUTPUT_HZ;
}
static int signed_byte(unsigned value) {
  return value < 128 ? (int)value : (int)value - 256;
}
static int sample_at(uint64_t cycle) {
  if (!Dbaa_PsgAdvance(audio.psg, cycle))
    return fail("PSG clock moved backwards");
  int16_t psg_left = 0, psg_right = 0;
  int a = 0, b = 0;
  uint32_t control = peek(0x04000082, 2);
  int enabled = !!(peek(0x04000084, 1) & 128);
  if (enabled) {
    Dbaa_PsgSample(audio.psg, &psg_left, &psg_right);
    if (Dbaa_PsgStatus(audio.psg) & 15)
      ++audio.cgb_samples;
    if (psg_left || psg_right)
      ++audio.psg_nonzero;
    if (audio.pcm_active && audio.ticks && audio.buffer_count &&
        (peek(0x04000102, 2) & 128)) {
      if (control & 0x4400)
        return fail("Timer1 DirectSound route has no native consumer");
      uint64_t elapsed = cycle - audio.block_cycle;
      uint32_t index = (uint32_t)((audio.block_offset +
                                   (elapsed ? elapsed - 1 : 0) / audio.ticks) %
                                  audio.buffer_count);
      a = (peek(0x040000C6, 2) & 0x8000)
              ? signed_byte(peek(audio.right_base + index, 1))
              : 0;
      b = (peek(0x040000D2, 2) & 0x8000)
              ? signed_byte(peek(audio.left_base + index, 1))
              : 0;
      if (a || b)
        ++audio.pcm_nonzero;
    }
  }
  DbaaDigitalSample sample;
  if (!Dbaa_DigitalMix(psg_left, psg_right, (int8_t)a, (int8_t)b,
                       (uint16_t)control, (uint16_t)peek(0x04000088, 2), 64,
                       &sample))
    return fail("invalid digital mixer configuration");
  audio.staging[audio.staged][0] = sample.left;
  audio.staging[audio.staged][1] = sample.right;
  audio.dac_clipped += sample.dac_clipped;
  audio.clipped += sample.pcm_clipped;
  ++audio.staged;
  ++audio.samples;
  return audio.staged < 1024 || flush();
}
int Dbaa_GameAudioAdvance(uint32_t cycles) {
  if (!audio.initialized)
    return 1;
  if (audio.error || audio.closed)
    return 0;
  uint64_t target = audio.cycles + cycles;
  uint64_t next = output_cycle(audio.samples + 1);
  while (next <= target) {
    if (!sample_at(next))
      return 0;
    next = output_cycle(audio.samples + 1);
  }
  if (!Dbaa_PsgAdvance(audio.psg, target))
    return fail("PSG clock moved backwards after sampling");
  audio.cycles = target;
  if (io_regs)
    io_regs[0x84] = Dbaa_PsgStatus(audio.psg);
  return 1;
}
int Dbaa_GameAudioWrite(uint32_t offset, uint32_t value, unsigned width) {
  if (!audio.initialized || offset < 0x60 || offset >= 0xA0)
    return 1;
  if (!Dbaa_PsgWrite(audio.psg, audio.cycles, 0x04000000u + offset, value,
                     width))
    return fail("unsupported PSG bus access");
  if (io_regs)
    io_regs[0x84] = Dbaa_PsgStatus(audio.psg);
  return 1;
}
void Dbaa_GameAudioVBlank(void) {
  if (!audio.initialized)
    return;
  uint32_t sound = peek(0x03007FF0, 4);
  uint32_t count = peek(sound + 16, 4), period = peek(sound + 11, 1);
  uint32_t counter = peek(sound + 4, 1), lock = peek(sound, 4);
  audio.pcm_active = 0;
  if (lock - 0x68736D53u > 1 || !count || count > DBAA_PCM_MAX || period < 2 ||
      period * count > 1584 || !counter || counter > period)
    return;
  audio.ticks = 65536u - peek(0x04000100, 2);
  if ((uint64_t)audio.ticks * count != DBAA_FRAME_CYCLES) {
    fail("unsupported game PCM frequency/period");
    return;
  }
  audio.right_base = sound + 0x350;
  audio.left_base = sound + 0x980;
  audio.block_offset = (period - counter) * count;
  audio.buffer_count = period * count;
  audio.block_cycle = audio.cycles;
  audio.pcm_active = 1;
  ++audio.pcm_vblanks;
}
const char *Dbaa_GameAudioError(void) {
  return audio.error ? audio.error : "none";
}
int Dbaa_GameAudioQueueDepth(size_t *frames) {
  if (!audio.initialized || !audio.device || audio.closed || audio.error || !frames)
    return 0;
  *frames = Dbaa_WasapiQueued() + audio.staged;
  return 1;
}
void Dbaa_GameAudioClose(void) {
  if (!audio.initialized || audio.closed)
    return;
  flush();
  if (audio.pcm && fclose(audio.pcm))
    fail("cannot close game PCM capture");
  audio.pcm = NULL;
  if (audio.device && !Dbaa_WasapiClose(&audio.device_stats))
    fail("cannot drain WASAPI game audio");
  Dbaa_PsgDestroy(audio.psg);
  audio.psg = NULL;
  audio.closed = 1;
  const char *path = getenv("DBAA_GAME_AUDIO_REPORT");
  FILE *report = path ? fopen(path, "wb") : stderr;
  if (!report)
    return;
  fprintf(
      report,
      "{\"ok\":%s,\"device_enabled\":%s,\"cycles\":%llu,"
      "\"stereo_samples\":%llu,\"pcm_vblanks\":%llu,\"cgb_samples\":%llu,"
      "\"psg_raw_nonzero_samples\":%llu,\"pcm_source_nonzero_samples\":%llu,"
      "\"dac_clipped\":%llu,\"clipped\":%llu,\"pcm_fnv1a64\":\"%016llx\","
      "\"error\":\"%s\","
      "\"device_submitted\":%llu,\"device_pcm_fnv1a64\":\"%016llx\","
      "\"endpoint_empty\":%llu,\"device_error\":%u,"
      "\"device_render_error\":%u,\"device_push_wait\":%u,\"device_drain_wait\":%u,"
      "\"device_last_padding\":%u,\"device_capacity\":%u,"
      "\"device_render_wakes\":%llu,\"device_queue_remaining\":%llu,"
      "\"device_first_empty\":%llu,\"device_last_empty\":%llu,"
      "\"device_empty_with_queued\":%llu,\"device_mmcss\":%u,"
      "\"device_max_push_gap_us\":%llu,\"device_max_gap_at_supplied\":%llu,"
      "\"device_max_gap_queued\":%llu,"
      "\"device_max_render_gap_us\":%llu,\"device_render_gap_at_submitted\":%llu,"
      "\"whole_game_pcm_rom_equal\":false}\n",
      audio.error ? "false" : "true", audio.device ? "true" : "false",
      (unsigned long long)audio.cycles, (unsigned long long)audio.samples,
      (unsigned long long)audio.pcm_vblanks,
      (unsigned long long)audio.cgb_samples,
      (unsigned long long)audio.psg_nonzero,
      (unsigned long long)audio.pcm_nonzero,
      (unsigned long long)audio.dac_clipped, (unsigned long long)audio.clipped,
      (unsigned long long)audio.hash, Dbaa_GameAudioError(),
      (unsigned long long)audio.device_stats.submitted,
      (unsigned long long)audio.device_stats.pcm_fnv1a64,
      (unsigned long long)audio.device_stats.endpoint_empty,
      audio.device_stats.error, audio.device_stats.render_error,
      audio.device_stats.push_wait_result, audio.device_stats.drain_wait_result,
      audio.device_stats.last_padding, audio.device_stats.capacity,
      (unsigned long long)audio.device_stats.render_wakes,
      (unsigned long long)audio.device_stats.queue_remaining,
      (unsigned long long)audio.device_stats.first_empty_at_submitted,
      (unsigned long long)audio.device_stats.last_empty_at_submitted,
      (unsigned long long)audio.device_stats.empty_with_queued,
      audio.device_stats.mmcss_enabled,
      (unsigned long long)audio.device_stats.max_push_gap_us,
      (unsigned long long)audio.device_stats.max_gap_at_supplied,
      (unsigned long long)audio.device_stats.max_gap_queued,
      (unsigned long long)audio.device_stats.max_render_gap_us,
      (unsigned long long)audio.device_stats.render_gap_at_submitted);
  if (path)
    fclose(report);
}
int Dbaa_GameAudioInit(int device_enabled) {
  memset(&audio, 0, sizeof(audio));
  audio.hash = UINT64_C(14695981039346656037);
  audio.psg = Dbaa_PsgCreate();
  if (!audio.psg)
    return fail("cannot allocate native PSG");
  audio.initialized = 1;
  atexit(Dbaa_GameAudioClose);
  const char *path = getenv("DBAA_GAME_PCM");
  if (path && !(audio.pcm = fopen(path, "wb")))
    return fail("cannot open game PCM capture");
  if (device_enabled) {
    audio.device = 1;
    if (!Dbaa_WasapiOpen())
      return fail("cannot open default WASAPI endpoint");
  }
  return 1;
}
