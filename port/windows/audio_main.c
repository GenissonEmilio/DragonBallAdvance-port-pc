/* Windows PCM audio host. This is an audio runner, not the complete game. */
#define COBJMACROS
#define INITGUID
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include "audio_runtime.h"
#include <audioclient.h>
#include <mmdeviceapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

typedef struct {
  IMMDeviceEnumerator *enumerator;
  IMMDevice *device;
  IAudioClient *client;
  IAudioRenderClient *render;
  IAudioClock *clock;
  HANDLE event, timer;
  UINT32 capacity;
  unsigned mix_rate, mix_channels, mix_bits;
  UINT64 clock_frequency, clock_start, clock_end;
  uint64_t submitted, events, max_late_qpc, playback_start, playback_end;
  uint64_t endpoint_empty_events, catch_up_frames;
  unsigned high_resolution, com, started;
  HRESULT error;
} AudioDevice;

typedef struct {
  unsigned song, player, stop_at, stop_all_at, restart_at;
} SongControl;

static uint64_t pcm_hash = UINT64_C(14695981039346656037);
static void consume(DbaaAudioRuntime *r, int16_t *samples, size_t frames) {
  Dbaa_AudioRuntimeRead(r, samples, frames);
  const uint8_t *bytes = (const uint8_t *)samples;
  for (size_t i = 0; i < frames * 4; ++i) {
    pcm_hash ^= bytes[i];
    pcm_hash *= UINT64_C(1099511628211);
  }
}

static int next_frame(DbaaAudioRuntime *r, const SongControl *control) {
  DbaaAudioStats stats;
  Dbaa_AudioRuntimeStats(r, &stats);
  if (stats.frames == control->stop_at &&
      !Dbaa_AudioRuntimeStopPlayer(r, control->player))
    return 0;
  if (stats.frames == control->stop_all_at && !Dbaa_AudioRuntimeStopAll(r))
    return 0;
  if (stats.frames == control->restart_at &&
      !Dbaa_AudioRuntimeStartSong(r, control->song))
    return 0;
  return Dbaa_AudioRuntimeFrame(r);
}

static volatile LONG stop_requested;
static BOOL WINAPI control_handler(DWORD type) {
  if (type == CTRL_C_EVENT || type == CTRL_BREAK_EVENT) {
    InterlockedExchange(&stop_requested, 1);
    return TRUE;
  }
  return FALSE;
}
static uint64_t counter(void) {
  LARGE_INTEGER value;
  QueryPerformanceCounter(&value);
  return (uint64_t)value.QuadPart;
}

static void device_close(AudioDevice *d) {
  if (d->client && d->started)
    IAudioClient_Stop(d->client);
  if (d->clock)
    IAudioClock_Release(d->clock);
  if (d->render)
    IAudioRenderClient_Release(d->render);
  if (d->client)
    IAudioClient_Release(d->client);
  if (d->device)
    IMMDevice_Release(d->device);
  if (d->enumerator)
    IMMDeviceEnumerator_Release(d->enumerator);
  if (d->event)
    CloseHandle(d->event);
  if (d->timer)
    CloseHandle(d->timer);
  if (d->com)
    CoUninitialize();
}

static int device_open(AudioDevice *d) {
  HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
  if (FAILED(hr)) {
    d->error = hr;
    return 0;
  }
  d->com = 1;
#define TRY(call)                                                              \
  do {                                                                         \
    hr = (call);                                                               \
    if (FAILED(hr))                                                            \
      goto failed;                                                             \
  } while (0)
  TRY(CoCreateInstance(&CLSID_MMDeviceEnumerator, NULL, CLSCTX_ALL,
                       &IID_IMMDeviceEnumerator, (void **)&d->enumerator));
  TRY(IMMDeviceEnumerator_GetDefaultAudioEndpoint(d->enumerator, eRender,
                                                  eConsole, &d->device));
  TRY(IMMDevice_Activate(d->device, &IID_IAudioClient, CLSCTX_ALL, NULL,
                         (void **)&d->client));
  WAVEFORMATEX format = {
      WAVE_FORMAT_PCM, 2, DBAA_OUTPUT_HZ, DBAA_OUTPUT_HZ * 4, 4, 16, 0};
  DWORD flags =
      AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM |
      AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY | AUDCLNT_STREAMFLAGS_NOPERSIST;
  TRY(IAudioClient_Initialize(d->client, AUDCLNT_SHAREMODE_SHARED, flags,
                              200000, 0, &format, NULL));
  d->event = CreateEventW(NULL, FALSE, FALSE, NULL);
  if (!d->event) {
    hr = HRESULT_FROM_WIN32(GetLastError());
    goto failed;
  }
  TRY(IAudioClient_SetEventHandle(d->client, d->event));
  TRY(IAudioClient_GetBufferSize(d->client, &d->capacity));
  TRY(IAudioClient_GetService(d->client, &IID_IAudioRenderClient,
                              (void **)&d->render));
  TRY(IAudioClient_GetService(d->client, &IID_IAudioClock, (void **)&d->clock));
  TRY(IAudioClock_GetFrequency(d->clock, &d->clock_frequency));
  WAVEFORMATEX *mix = NULL;
  TRY(IAudioClient_GetMixFormat(d->client, &mix));
  d->mix_rate = mix->nSamplesPerSec;
  d->mix_channels = mix->nChannels;
  d->mix_bits = mix->wBitsPerSample;
  CoTaskMemFree(mix);
  d->timer = CreateWaitableTimerExW(NULL, NULL, 2, TIMER_ALL_ACCESS);
  d->high_resolution = d->timer != NULL;
  if (!d->timer)
    d->timer = CreateWaitableTimerExW(NULL, NULL, 0, TIMER_ALL_ACCESS);
  if (!d->timer) {
    hr = HRESULT_FROM_WIN32(GetLastError());
    goto failed;
  }
  return 1;
failed:
  d->error = hr;
  return 0;
#undef TRY
}

static int device_pump(AudioDevice *d, DbaaAudioRuntime *r, int draining) {
  UINT32 padding = 0;
  HRESULT hr = IAudioClient_GetCurrentPadding(d->client, &padding);
  if (FAILED(hr) || padding > d->capacity) {
    d->error = FAILED(hr) ? hr : E_UNEXPECTED;
    return 0;
  }
  UINT32 available = d->capacity - padding;
  if (d->started && !draining && !padding)
    ++d->endpoint_empty_events;
  if (draining && available > Dbaa_AudioRuntimeQueued(r))
    available = (UINT32)Dbaa_AudioRuntimeQueued(r);
  if (!available)
    return 1;
  BYTE *data = NULL;
  hr = IAudioRenderClient_GetBuffer(d->render, available, &data);
  if (FAILED(hr)) {
    d->error = hr;
    return 0;
  }
  consume(r, (int16_t *)data, available);
  hr = IAudioRenderClient_ReleaseBuffer(d->render, available, 0);
  if (FAILED(hr)) {
    d->error = hr;
    return 0;
  }
  d->submitted += available;
  return 1;
}

static int device_run(AudioDevice *d, DbaaAudioRuntime *r, unsigned frames,
                      uint64_t frequency, unsigned stall_ms,
                      const SongControl *control) {
  unsigned produced = 0;
  const size_t frame_max =
      (DBAA_FRAME_CYCLES * (uint64_t)DBAA_OUTPUT_HZ + DBAA_CPU_HZ - 1) /
      DBAA_CPU_HZ;
  /* Endpoint capacity plus two producer frames protects both initial fill
   * and the first Windows wake interval. Short streams can drain partially. */
  while (produced < frames &&
         Dbaa_AudioRuntimeQueued(r) < d->capacity + 2 * frame_max) {
    if (!next_frame(r, control))
      return 0;
    ++produced;
  }
  if (!device_pump(d, r, 1))
    return 0;
  d->error = IAudioClock_GetPosition(d->clock, &d->clock_start, NULL);
  if (FAILED(d->error))
    return 0;
  d->playback_start = counter();
  d->error = IAudioClient_Start(d->client);
  if (FAILED(d->error))
    return 0;
  d->started = 1;
  uint64_t origin = counter(), tick = 1;
  int stalled = 0;
  while (produced < frames && !stop_requested) {
    uint64_t deadline = origin + Dbaa_AudioDeadline(tick, frequency);
    uint64_t now = counter();
    unsigned catchup = 0;
    while (now >= deadline && produced < frames) {
      uint64_t late = now - deadline;
      if (late > d->max_late_qpc)
        d->max_late_qpc = late;
      if (++catchup > 8) {
        d->error = HRESULT_FROM_WIN32(ERROR_TIMEOUT);
        return 0;
      }
      if (catchup > 1)
        ++d->catch_up_frames;
      if (!next_frame(r, control))
        return 0;
      ++produced;
      ++tick;
      deadline = origin + Dbaa_AudioDeadline(tick, frequency);
      now = counter();
    }
    if (!device_pump(d, r, produced == frames))
      return 0;
    if (produced == frames)
      break;
    if (stall_ms && !stalled && tick > 10) {
      Sleep(stall_ms); /* Explicit fault-injection option for tests only. */
      stalled = 1;
      continue;
    }
    now = counter();
    if (now >= deadline)
      continue;
    uint64_t delay = ((deadline - now) * 10000000u + frequency - 1) / frequency;
    LARGE_INTEGER due;
    due.QuadPart = -(LONGLONG)(delay ? delay : 1);
    if (!SetWaitableTimer(d->timer, &due, 0, NULL, NULL, FALSE)) {
      d->error = HRESULT_FROM_WIN32(GetLastError());
      return 0;
    }
    HANDLE waits[2] = {d->timer, d->event};
    DWORD result = WaitForMultipleObjects(2, waits, FALSE, 1000);
    if (result == WAIT_OBJECT_0 + 1)
      ++d->events;
    else if (result != WAIT_OBJECT_0) {
      d->error = result == WAIT_FAILED ? HRESULT_FROM_WIN32(GetLastError())
                                       : HRESULT_FROM_WIN32(ERROR_TIMEOUT);
      return 0;
    }
  }
  /* Submit the tail, then wait for endpoint consumption. Never add silence
   * merely to pad a normal shutdown; all waits have a bounded timeout. */
  uint64_t timeout = counter() + frequency * 3;
  while (!stop_requested) {
    if (!device_pump(d, r, 1))
      return 0;
    UINT32 padding;
    HRESULT hr = IAudioClient_GetCurrentPadding(d->client, &padding);
    if (FAILED(hr)) {
      d->error = hr;
      return 0;
    }
    if (!padding && !Dbaa_AudioRuntimeQueued(r))
      break;
    if (counter() >= timeout) {
      d->error = HRESULT_FROM_WIN32(ERROR_TIMEOUT);
      return 0;
    }
    DWORD result = WaitForSingleObject(d->event, 100);
    if (result == WAIT_OBJECT_0)
      ++d->events;
    else if (result == WAIT_FAILED) {
      d->error = HRESULT_FROM_WIN32(GetLastError());
      return 0;
    }
  }
  d->error = IAudioClock_GetPosition(d->clock, &d->clock_end, NULL);
  d->playback_end = counter();
  return SUCCEEDED(d->error);
}

static void le32(FILE *f, uint32_t n) {
  for (unsigned i = 0; i < 4; ++i)
    fputc((int)((n >> (i * 8)) & 255), f);
}
static int offline(DbaaAudioRuntime *r, const char *path, unsigned frames,
                   const SongControl *control) {
  FILE *f = fopen(path, "wb");
  if (!f)
    return 0;
  fwrite("RIFF", 1, 4, f);
  le32(f, 0);
  fwrite("WAVEfmt ", 1, 8, f);
  le32(f, 16);
  fputc(1, f);
  fputc(0, f);
  fputc(2, f);
  fputc(0, f);
  le32(f, DBAA_OUTPUT_HZ);
  le32(f, DBAA_OUTPUT_HZ * 4);
  fputc(4, f);
  fputc(0, f);
  fputc(16, f);
  fputc(0, f);
  fwrite("data", 1, 4, f);
  le32(f, 0);
  uint32_t bytes = 0;
  int16_t samples[2048];
  for (unsigned i = 0; i < frames; ++i) {
    if (!next_frame(r, control)) {
      fclose(f);
      return 0;
    }
    size_t n = Dbaa_AudioRuntimeQueued(r);
    if (n > 1024) {
      fclose(f);
      return 0;
    }
    consume(r, samples, n);
    if (fwrite(samples, 4, n, f) != n) {
      fclose(f);
      return 0;
    }
    bytes += (uint32_t)n * 4;
  }
  if (fseek(f, 4, SEEK_SET)) {
    fclose(f);
    return 0;
  }
  le32(f, bytes + 36);
  if (fseek(f, 40, SEEK_SET)) {
    fclose(f);
    return 0;
  }
  le32(f, bytes);
  return fclose(f) == 0;
}

static unsigned number(const char *s, unsigned maximum) {
  char *end;
  unsigned long n = strtoul(s, &end, 10);
  return !*s || *end || n > maximum ? UINT_MAX : (unsigned)n;
}
int main(int argc, char **argv) {
  const char *rom_path = "baserom.gba", *wav = NULL, *report_path = NULL;
  unsigned frames = 180, index = 5, gain = 64, stall = 0;
  SongControl control = {UINT_MAX, 0, UINT_MAX, UINT_MAX, UINT_MAX};
  int demo = 0;
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--demo"))
      demo = 1;
    else if (i + 1 < argc && !strcmp(argv[i], "--rom"))
      rom_path = argv[++i];
    else if (i + 1 < argc && !strcmp(argv[i], "--wav"))
      wav = argv[++i];
    else if (i + 1 < argc && !strcmp(argv[i], "--report"))
      report_path = argv[++i];
    else if (i + 1 < argc && !strcmp(argv[i], "--frames"))
      frames = number(argv[++i], 1000000);
    else if (i + 1 < argc && !strcmp(argv[i], "--mode"))
      index = number(argv[++i], 12);
    else if (i + 1 < argc && !strcmp(argv[i], "--gain"))
      gain = number(argv[++i], 256);
    else if (i + 1 < argc && !strcmp(argv[i], "--stall-ms"))
      stall = number(argv[++i], 1000);
    else if (i + 1 < argc && !strcmp(argv[i], "--song"))
      control.song = number(argv[++i], DBAA_SONG_COUNT - 1);
    else if (i + 1 < argc && !strcmp(argv[i], "--stop-at"))
      control.stop_at = number(argv[++i], 1000000);
    else if (i + 1 < argc && !strcmp(argv[i], "--stop-all-at"))
      control.stop_all_at = number(argv[++i], 1000000);
    else if (i + 1 < argc && !strcmp(argv[i], "--restart-at"))
      control.restart_at = number(argv[++i], 1000000);
    else {
      fprintf(
          stderr,
          "Usage: dbaa_audio [--rom file] [--demo] [--frames N] [--mode 1..12] "
          "[--gain 0..256] [--song 0..969] [--stop-at frame] "
          "[--stop-all-at frame] [--restart-at frame] "
          "[--wav file] [--report file] [--stall-ms N]\n");
      return 2;
    }
  }
  if (!frames || frames == UINT_MAX || !index || index == UINT_MAX ||
      gain == UINT_MAX || stall == UINT_MAX)
    return 2;
  /* Explicit song arguments and scheduled controls require a valid song.
   * A parser sentinel may mean absence or invalid input, so check each flag. */
  for (int i = 1; i < argc; ++i) {
    if (!strcmp(argv[i], "--song") && control.song == UINT_MAX)
      return 2;
    if ((!strcmp(argv[i], "--stop-at") && control.stop_at == UINT_MAX) ||
        (!strcmp(argv[i], "--stop-all-at") &&
         control.stop_all_at == UINT_MAX) ||
        (!strcmp(argv[i], "--restart-at") && control.restart_at == UINT_MAX))
      return 2;
  }
  if ((demo && control.song != UINT_MAX) ||
      (control.song == UINT_MAX &&
       (control.stop_at != UINT_MAX || control.stop_all_at != UINT_MAX ||
        control.restart_at != UINT_MAX)))
    return 2;
  FILE *f = fopen(rom_path, "rb");
  if (!f) {
    fprintf(stderr, "Cannot open ROM\n");
    return 2;
  }
  uint8_t *rom = malloc(0x1000001);
  size_t n = rom ? fread(rom, 1, 0x1000001, f) : 0;
  fclose(f);
  DbaaAudioRuntime *r = Dbaa_AudioRuntimeCreate(rom, n);
  if (r && control.song != UINT_MAX) {
    size_t offset = 0xA69068u + control.song * 8u + 4;
    control.player = rom[offset] | ((unsigned)rom[offset + 1] << 8);
  }
  free(rom);
  if (!r) {
    fprintf(stderr, "Requires exact USA BDVE rev0 ROM (CRC32 7d7306df)\n");
    return 2;
  }
  int ok = Dbaa_AudioRuntimeInitialize(r) && Dbaa_AudioRuntimeMode(r, index);
  Dbaa_AudioRuntimeGain(r, gain);
  if (ok && demo)
    ok = Dbaa_AudioRuntimeDemo(r);
  if (ok && control.song != UINT_MAX)
    ok = Dbaa_AudioRuntimeStartSong(r, control.song);
  LARGE_INTEGER frequency;
  if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0) {
    Dbaa_AudioRuntimeDestroy(r);
    return 1;
  }
  uint64_t start = counter();
  AudioDevice device = {0};
  SetConsoleCtrlHandler(control_handler, TRUE);
  if (ok) {
    if (wav)
      ok = offline(r, wav, frames, &control);
    else
      ok = device_open(&device) &&
           device_run(&device, r, frames, (uint64_t)frequency.QuadPart, stall,
                      &control);
  }
  uint64_t elapsed = counter() - start;
  DbaaAudioStats stats;
  Dbaa_AudioRuntimeStats(r, &stats);
  if (!ok)
    fprintf(stderr, "Audio failed: %s; HRESULT 0x%08lx\n",
            Dbaa_AudioRuntimeError(r), (unsigned long)device.error);
  FILE *report = report_path ? fopen(report_path, "wb") : stdout;
  if (!report)
    ok = 0;
  else {
    fprintf(
        report,
        "{\n  \"ok\": %s,\n  \"backend\": \"%s\",\n  \"synthetic_demo\": %s,\n"
        "  \"song_id\": %d,\n  \"song_player_index\": %d,\n"
        "  \"stop_at_frame\": %d,\n  \"stop_all_at_frame\": %d,\n"
        "  \"restart_at_frame\": %d,\n"
        "  \"consumed_pcm_fnv1a64\": \"%016llx\",\n"
        "  \"frames\": %llu,\n  \"source_samples\": %llu,\n  "
        "\"converted_samples\": %llu,\n"
        "  \"consumed_samples\": %llu,\n  \"underrun_samples\": %llu,\n  "
        "\"overflow_samples\": %llu,\n"
        "  \"max_queued\": %llu,\n  \"faults\": %llu,\n  "
        "\"cgb_active_frames\": %llu,\n"
        "  \"output_hz\": 48000,\n  \"gain_q8\": %u,\n  \"qpc_frequency\": "
        "%llu,\n"
        "  \"elapsed_qpc\": %llu,\n  \"max_late_qpc\": %llu,\n"
        "  \"playback_qpc\": %llu,\n"
        "  \"endpoint_empty_events\": %llu,\n  \"catch_up_frames\": %llu,\n"
        "  \"endpoint_capacity\": %u,\n  \"submitted_frames\": %llu,\n  "
        "\"device_mix_rate\": %u,\n  \"device_mix_channels\": %u,\n  "
        "\"device_mix_bits\": %u,\n  "
        "\"audio_events\": %llu,\n"
        "  \"audio_clock_frequency\": %llu,\n  \"audio_clock_start\": %llu,\n"
        "  \"audio_clock_end\": %llu,\n  \"high_resolution_timer\": %s,\n"
        "  \"hresult\": %lu,\n  \"full_game_boot\": false,\n  "
        "\"psg_synthesis\": false,\n"
        "  \"physical_audibility_confirmed\": false\n}\n",
        ok ? "true" : "false", wav ? "offline_wav" : "wasapi_shared_event",
        demo ? "true" : "false",
        control.song == UINT_MAX ? -1 : (int)control.song,
        control.song == UINT_MAX ? -1 : (int)control.player,
        control.stop_at == UINT_MAX ? -1 : (int)control.stop_at,
        control.stop_all_at == UINT_MAX ? -1 : (int)control.stop_all_at,
        control.restart_at == UINT_MAX ? -1 : (int)control.restart_at,
        (unsigned long long)pcm_hash, (unsigned long long)stats.frames,
        (unsigned long long)stats.source_samples,
        (unsigned long long)stats.converted_samples,
        (unsigned long long)stats.consumed_samples,
        (unsigned long long)stats.underrun_samples,
        (unsigned long long)stats.overflow_samples,
        (unsigned long long)stats.max_queued, (unsigned long long)stats.faults,
        (unsigned long long)stats.cgb_active_frames, gain,
        (unsigned long long)frequency.QuadPart, (unsigned long long)elapsed,
        (unsigned long long)device.max_late_qpc,
        (unsigned long long)(device.playback_end - device.playback_start),
        (unsigned long long)device.endpoint_empty_events,
        (unsigned long long)device.catch_up_frames, device.capacity,
        (unsigned long long)device.submitted, device.mix_rate,
        device.mix_channels, device.mix_bits, (unsigned long long)device.events,
        (unsigned long long)device.clock_frequency,
        (unsigned long long)device.clock_start,
        (unsigned long long)device.clock_end,
        device.high_resolution ? "true" : "false", (unsigned long)device.error);
    if (report_path && fclose(report))
      ok = 0;
  }
  SetConsoleCtrlHandler(control_handler, FALSE);
  device_close(&device);
  Dbaa_AudioRuntimeDestroy(r);
  return ok ? 0 : 1;
}
