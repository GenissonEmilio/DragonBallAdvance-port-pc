/* 48 kHz stereo PCM16 sink. The event-driven worker owns its COM interfaces;
 * the producer submits game audio without sharing game RAM with that worker. */
#define COBJMACROS
#define INITGUID
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include "wasapi_sink.h"
#include <audioclient.h>
#include <mmdeviceapi.h>
#include <avrt.h>
#include <string.h>
#include <windows.h>

#define RING_FRAMES 16384u
#define PREFILL_FRAMES 4800u
static struct {
  HANDLE thread, ready, stop, data, space;
  CRITICAL_SECTION lock;
  int initialized, complete;
  size_t head, queued;
  int16_t ring[RING_FRAMES][2];
  DbaaWasapiStats stats;
  uint64_t last_push, frequency;
} sink;

static DWORD WINAPI render_thread(void *unused) {
  (void)unused;
  IMMDeviceEnumerator *enumerator = NULL;
  IMMDevice *device = NULL;
  IAudioClient *client = NULL;
  IAudioRenderClient *render = NULL;
  HANDLE event = NULL;
  HANDLE task = NULL;
  int com = 0, started = 0;
  uint64_t previous_render = 0;
  UINT32 capacity = 0;
  HRESULT hr = CoInitializeEx(NULL, COINIT_MULTITHREADED);
  if (FAILED(hr))
    goto done;
  com = 1;
#define TRY(call)                                                              \
  do {                                                                         \
    hr = (call);                                                               \
    if (FAILED(hr))                                                            \
      goto done;                                                               \
  } while (0)
  TRY(CoCreateInstance(&CLSID_MMDeviceEnumerator, NULL, CLSCTX_ALL,
                       &IID_IMMDeviceEnumerator, (void **)&enumerator));
  TRY(IMMDeviceEnumerator_GetDefaultAudioEndpoint(enumerator, eRender, eConsole,
                                                  &device));
  TRY(IMMDevice_Activate(device, &IID_IAudioClient, CLSCTX_ALL, NULL,
                         (void **)&client));
  WAVEFORMATEX format = {WAVE_FORMAT_PCM, 2, 48000, 192000, 4, 16, 0};
  TRY(IAudioClient_Initialize(client, AUDCLNT_SHAREMODE_SHARED,
                              AUDCLNT_STREAMFLAGS_EVENTCALLBACK |
                                  AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM |
                                  AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY |
                                  AUDCLNT_STREAMFLAGS_NOPERSIST,
                              500000, 0, &format, NULL));
  event = CreateEventW(NULL, FALSE, FALSE, NULL);
  if (!event) {
    hr = HRESULT_FROM_WIN32(GetLastError());
    goto done;
  }
  TRY(IAudioClient_SetEventHandle(client, event));
  TRY(IAudioClient_GetBufferSize(client, &capacity));
  sink.stats.capacity = capacity;
  TRY(IAudioClient_GetService(client, &IID_IAudioRenderClient,
                              (void **)&render));
  DWORD task_index = 0;
  task = AvSetMmThreadCharacteristicsW(L"Pro Audio", &task_index);
  if (task) {
    sink.stats.mmcss_enabled = 1;
    AvSetMmThreadPriority(task, AVRT_PRIORITY_HIGH);
  }
  SetEvent(sink.ready);
  for (;;) {
    EnterCriticalSection(&sink.lock);
    size_t queued = sink.queued;
    int complete = sink.complete;
    LeaveCriticalSection(&sink.lock);
    if (WaitForSingleObject(sink.stop, 0) == WAIT_OBJECT_0)
      break;
    if (!started && queued < PREFILL_FRAMES && !complete) {
      HANDLE events[] = {sink.stop, sink.data};
      WaitForMultipleObjects(2, events, FALSE, 100);
      continue;
    }
    UINT32 padding;
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    if (started && previous_render) {
      uint64_t gap = ((uint64_t)now.QuadPart - previous_render) * 1000000 / sink.frequency;
      if (gap > sink.stats.max_render_gap_us) {
        sink.stats.max_render_gap_us = gap;
        sink.stats.render_gap_at_submitted = sink.stats.submitted;
      }
    }
    previous_render = (uint64_t)now.QuadPart;
    TRY(IAudioClient_GetCurrentPadding(client, &padding));
    sink.stats.last_padding = padding;
    ++sink.stats.render_wakes;
    if (padding > capacity) {
      hr = E_UNEXPECTED;
      goto done;
    }
    if (started && !padding && !complete) {
      if (!sink.stats.endpoint_empty)
        sink.stats.first_empty_at_submitted = sink.stats.submitted;
      sink.stats.last_empty_at_submitted = sink.stats.submitted;
      sink.stats.empty_with_queued += !!queued;
      ++sink.stats.endpoint_empty;
    }
    if (complete && !queued && !padding)
      break;
    UINT32 frames = capacity - padding;
    if (frames > queued)
      frames = (UINT32)queued;
    if (frames) {
      BYTE *buffer;
      TRY(IAudioRenderClient_GetBuffer(render, frames, &buffer));
      EnterCriticalSection(&sink.lock);
      for (UINT32 i = 0; i < frames; ++i) {
        memcpy(buffer + 4 * i, sink.ring[sink.head], 4);
        sink.head = (sink.head + 1) % RING_FRAMES;
      }
      sink.queued -= frames;
      LeaveCriticalSection(&sink.lock);
      for (size_t i = 0; i < (size_t)frames * 4; ++i) {
        sink.stats.pcm_fnv1a64 ^= buffer[i];
        sink.stats.pcm_fnv1a64 *= UINT64_C(1099511628211);
      }
      TRY(IAudioRenderClient_ReleaseBuffer(render, frames, 0));
      sink.stats.submitted += frames;
      SetEvent(sink.space);
    }
    if (!started && frames) {
      TRY(IAudioClient_Start(client));
      started = 1;
    }
    HANDLE events[] = {sink.stop, event};
    WaitForMultipleObjects(2, events, FALSE, 100);
  }
done:
  sink.stats.render_error = (uint32_t)hr;
  sink.stats.error = (uint32_t)hr;
  SetEvent(sink.ready);
  SetEvent(sink.space);
  if (started)
    IAudioClient_Stop(client);
  if (render)
    IAudioRenderClient_Release(render);
  if (client)
    IAudioClient_Release(client);
  if (device)
    IMMDevice_Release(device);
  if (enumerator)
    IMMDeviceEnumerator_Release(enumerator);
  if (event)
    CloseHandle(event);
  if (task)
    AvRevertMmThreadCharacteristics(task);
  if (com)
    CoUninitialize();
  return 0;
#undef TRY
}
int Dbaa_WasapiOpen(void) {
  if (sink.initialized)
    return 0;
  memset(&sink, 0, sizeof(sink));
  InitializeCriticalSection(&sink.lock);
  sink.initialized = 1;
  sink.stats.pcm_fnv1a64 = UINT64_C(14695981039346656037);
  LARGE_INTEGER frequency;
  QueryPerformanceFrequency(&frequency);
  sink.frequency = (uint64_t)frequency.QuadPart;
  sink.ready = CreateEventW(NULL, TRUE, FALSE, NULL);
  sink.stop = CreateEventW(NULL, TRUE, FALSE, NULL);
  sink.data = CreateEventW(NULL, FALSE, FALSE, NULL);
  sink.space = CreateEventW(NULL, FALSE, FALSE, NULL);
  if (!sink.ready || !sink.stop || !sink.data || !sink.space)
    return 0;
  sink.thread = CreateThread(NULL, 0, render_thread, NULL, 0, NULL);
  if (!sink.thread || WaitForSingleObject(sink.ready, 5000) != WAIT_OBJECT_0)
    return 0;
  return !FAILED((HRESULT)sink.stats.error) &&
         WaitForSingleObject(sink.thread, 0) == WAIT_TIMEOUT;
}
int Dbaa_WasapiPush(const int16_t *stereo, size_t frames) {
  if (!sink.initialized || !sink.thread || (!stereo && frames))
    return 0;
  LARGE_INTEGER now;
  QueryPerformanceCounter(&now);
  if (sink.last_push) {
    uint64_t gap = ((uint64_t)now.QuadPart - sink.last_push) * 1000000 / sink.frequency;
    if (gap > sink.stats.max_push_gap_us) {
      sink.stats.max_push_gap_us = gap;
      sink.stats.max_gap_at_supplied = sink.stats.supplied;
      sink.stats.max_gap_queued = Dbaa_WasapiQueued();
    }
  }
  sink.last_push = (uint64_t)now.QuadPart;
  while (frames) {
    if (WaitForSingleObject(sink.thread, 0) != WAIT_TIMEOUT)
      return 0;
    EnterCriticalSection(&sink.lock);
    size_t count = RING_FRAMES - sink.queued;
    if (count > frames)
      count = frames;
    for (size_t i = 0; i < count; ++i) {
      size_t tail = (sink.head + sink.queued + i) % RING_FRAMES;
      memcpy(sink.ring[tail], stereo + 2 * i, 4);
    }
    sink.queued += count;
    sink.stats.supplied += count;
    if (sink.queued > sink.stats.queue_max)
      sink.stats.queue_max = sink.queued;
    LeaveCriticalSection(&sink.lock);
    stereo += 2 * count;
    frames -= count;
    SetEvent(sink.data);
    if (!count) {
      HANDLE events[] = {sink.thread, sink.space};
      DWORD result = WaitForMultipleObjects(2, events, FALSE, 2000);
      if (result != WAIT_OBJECT_0 + 1) {
        sink.stats.push_wait_result = result;
        return 0;
      }
    }
  }
  return 1;
}
size_t Dbaa_WasapiQueued(void) {
  if (!sink.initialized)
    return 0;
  EnterCriticalSection(&sink.lock);
  size_t queued = sink.queued;
  LeaveCriticalSection(&sink.lock);
  return queued;
}
int Dbaa_WasapiClose(DbaaWasapiStats *stats) {
  if (!sink.initialized)
    return 0;
  EnterCriticalSection(&sink.lock);
  sink.complete = 1;
  LeaveCriticalSection(&sink.lock);
  if (sink.data)
    SetEvent(sink.data);
  DWORD result = sink.thread ? WaitForSingleObject(sink.thread, 2000) : WAIT_OBJECT_0;
  sink.stats.drain_wait_result = result;
  if (result != WAIT_OBJECT_0) {
    SetEvent(sink.stop);
    WaitForSingleObject(sink.thread, INFINITE);
    if (!FAILED((HRESULT)sink.stats.error))
      sink.stats.error = (uint32_t)HRESULT_FROM_WIN32(ERROR_TIMEOUT);
  }
  sink.stats.queue_remaining = sink.queued;
  if (stats)
    *stats = sink.stats;
  int ok = !FAILED((HRESULT)sink.stats.error) &&
           sink.stats.supplied == sink.stats.submitted;
  HANDLE handles[] = {sink.thread, sink.ready, sink.stop, sink.data,
                      sink.space};
  for (unsigned i = 0; i < 5; ++i)
    if (handles[i])
      CloseHandle(handles[i]);
  DeleteCriticalSection(&sink.lock);
  sink.initialized = 0;
  return ok;
}
