/* Win32 window and GDI live on a presentation thread. The game publishes the
 * latest framebuffer without waiting for GDI, so a slow desktop cannot block
 * the PCM producer. Software rendering and emulated game time are unchanged. */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include "game_window.h"
#include "audio_runtime.h"
#include <windows.h>
#ifdef DBAA_GAME_AUDIO_ENABLED
#include "game_audio.h"
#include <avrt.h>
#include <stdio.h>
static HANDLE game_task;
#endif
#include <string.h>

static HANDLE thread, ready, stop, submitted, timer;
static HWND window;
static BITMAPINFO bitmap;
static uint32_t framebuffer[240 * 160], pending[240 * 160];
static SRWLOCK frame_lock = SRWLOCK_INIT;
static uint64_t origin, frequency, frames;
static volatile LONG quit, held_keys, opened;

static LONG key_bit(WPARAM key) {
  static const int keys[10] = {'Z', 'X', VK_BACK, VK_RETURN, VK_RIGHT,
                              VK_LEFT, VK_UP, VK_DOWN, 'S', 'A'};
  for (unsigned i = 0; i < 10; ++i)
    if (key == (WPARAM)keys[i])
      return (LONG)(1u << i);
  return 0;
}
static uint64_t counter(void) {
  LARGE_INTEGER n;
  QueryPerformanceCounter(&n);
  return (uint64_t)n.QuadPart;
}
static void paint(HDC dc) {
  RECT rect;
  GetClientRect(window, &rect);
  int width = rect.right, height = rect.bottom;
  int scale = width / 240 < height / 160 ? width / 240 : height / 160;
  if (scale < 1)
    scale = 1;
  int w = 240 * scale, h = 160 * scale;
  FillRect(dc, &rect, (HBRUSH)GetStockObject(BLACK_BRUSH));
  SetStretchBltMode(dc, COLORONCOLOR);
  StretchDIBits(dc, (width - w) / 2, (height - h) / 2, w, h, 0, 0, 240, 160,
                framebuffer, &bitmap, DIB_RGB_COLORS, SRCCOPY);
}
static LRESULT CALLBACK procedure(HWND hwnd, UINT message, WPARAM w, LPARAM l) {
  switch (message) {
  case WM_KILLFOCUS:
    InterlockedExchange(&held_keys, 0);
    return 0;
  case WM_KEYDOWN:
    InterlockedOr(&held_keys, key_bit(w));
    return 0;
  case WM_KEYUP:
    InterlockedAnd(&held_keys, ~key_bit(w));
    return 0;
  case WM_CLOSE:
    InterlockedExchange(&quit, 1);
    return 0;
  case WM_PAINT: {
    PAINTSTRUCT state;
    HDC dc = BeginPaint(hwnd, &state);
    paint(dc);
    EndPaint(hwnd, &state);
    return 0;
  }
  case WM_ERASEBKGND:
    return 1;
  default:
    return DefWindowProcW(hwnd, message, w, l);
  }
}
static DWORD WINAPI present_thread(void *unused) {
  (void)unused;
  WNDCLASSW type = {0};
  type.lpfnWndProc = procedure;
  type.hInstance = GetModuleHandleW(NULL);
  type.hCursor = LoadCursorW(NULL, MAKEINTRESOURCEW(32512));
  type.lpszClassName = L"DbaaNativeWindow";
  if (!RegisterClassW(&type) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
    goto failed;
  RECT size = {0, 0, 720, 480};
  AdjustWindowRect(&size, WS_OVERLAPPEDWINDOW, FALSE);
  window = CreateWindowW(type.lpszClassName,
                        L"Dragon Ball: Advanced Adventure | Setas: mover | "
                        L"Z/X: A/B | Enter: Start", WS_OVERLAPPEDWINDOW,
                        CW_USEDEFAULT, CW_USEDEFAULT, size.right - size.left,
                        size.bottom - size.top, NULL, NULL, type.hInstance, NULL);
  if (!window)
    goto failed;
#ifdef DBAA_WINDOW_TEST
  ShowWindow(window, SW_HIDE);
#else
  ShowWindow(window, SW_SHOW);
#endif
  InterlockedExchange(&opened, 1);
  SetEvent(ready);
  for (;;) {
    HANDLE events[] = {stop, submitted};
    DWORD result = MsgWaitForMultipleObjects(2, events, FALSE, INFINITE, QS_ALLINPUT);
    if (result == WAIT_OBJECT_0 || result == WAIT_FAILED)
      break;
    if (result == WAIT_OBJECT_0 + 1) {
      AcquireSRWLockExclusive(&frame_lock);
      memcpy(framebuffer, pending, sizeof(framebuffer));
      ReleaseSRWLockExclusive(&frame_lock);
      /* Never hold the handoff lock while calling into the desktop. */
      HDC dc = GetDC(window);
      paint(dc);
      ReleaseDC(window, dc);
    }
    MSG message;
    while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
      if (message.message == WM_QUIT) {
        InterlockedExchange(&quit, 1);
        goto done;
      }
      TranslateMessage(&message);
      DispatchMessageW(&message);
    }
  }
done:
  DestroyWindow(window);
  window = NULL;
  return 0;
failed:
  InterlockedExchange(&opened, -1);
  InterlockedExchange(&quit, 1);
  SetEvent(ready);
  return 1;
}
int Dbaa_WindowOpen(void) {
  if (thread)
    return -1;
  quit = held_keys = opened = 0;
  frames = 0;
  bitmap.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bitmap.bmiHeader.biWidth = 240;
  bitmap.bmiHeader.biHeight = -160;
  bitmap.bmiHeader.biPlanes = 1;
  bitmap.bmiHeader.biBitCount = 32;
  ready = CreateEventW(NULL, TRUE, FALSE, NULL);
  stop = CreateEventW(NULL, TRUE, FALSE, NULL);
  submitted = CreateEventW(NULL, FALSE, FALSE, NULL);
  timer = CreateWaitableTimerExW(NULL, NULL, 2, TIMER_ALL_ACCESS);
  if (!timer)
    timer = CreateWaitableTimerExW(NULL, NULL, 0, TIMER_ALL_ACCESS);
  if (!ready || !stop || !submitted || !timer)
    goto failed;
  thread = CreateThread(NULL, 0, present_thread, NULL, 0, NULL);
  if (!thread || WaitForSingleObject(ready, 10000) != WAIT_OBJECT_0 || opened != 1)
    goto failed;
  LARGE_INTEGER q;
  QueryPerformanceFrequency(&q);
  frequency = (uint64_t)q.QuadPart;
  origin = counter();
#ifdef DBAA_GAME_AUDIO_ENABLED
  DWORD task_index = 0;
  game_task = AvSetMmThreadCharacteristicsW(L"Games", &task_index);
  if (game_task)
    AvSetMmThreadPriority(game_task, AVRT_PRIORITY_HIGH);
  fprintf(stderr, "[window] Games MMCSS %s; asynchronous GDI\n", game_task ? "active" : "unavailable");
#endif
  return 0;
failed:
  Dbaa_WindowClose();
  return -1;
}
void Dbaa_WindowPresent(const uint32_t *pixels) {
  if (TryAcquireSRWLockExclusive(&frame_lock)) {
    memcpy(pending, pixels, sizeof(pending));
    ReleaseSRWLockExclusive(&frame_lock);
    SetEvent(submitted);
  }
}
int Dbaa_WindowPoll(uint16_t *pressed) {
  *pressed = (uint16_t)InterlockedCompareExchange(&held_keys, 0, 0);
  return (int)InterlockedCompareExchange(&quit, 0, 0);
}
void Dbaa_WindowPace(void) {
  uint64_t deadline = origin + Dbaa_AudioDeadline(++frames, frequency);
  uint64_t now = counter();
#ifdef DBAA_GAME_AUDIO_ENABLED
  size_t queued;
  if (Dbaa_GameAudioQueueDepth(&queued)) {
    if (queued < 3600) {
      origin = now - Dbaa_AudioDeadline(frames, frequency);
      return;
    }
    int64_t correction = ((int64_t)queued - 4800) * (int64_t)frequency / (48000 * 32);
    int64_t limit = (int64_t)frequency / 1000;
    if (correction < -limit) correction = -limit;
    if (correction > limit) correction = limit;
    origin = (uint64_t)((int64_t)origin + correction);
    deadline = (uint64_t)((int64_t)deadline + correction);
  }
#endif
  if (now > deadline && now - deadline > frequency / 4) {
    origin += now - deadline;
    return;
  }
  while (now < deadline) {
    uint64_t ticks = (deadline - now) * UINT64_C(10000000) / frequency;
    LARGE_INTEGER due;
    due.QuadPart = -(LONGLONG)(ticks ? ticks : 1);
    if (!SetWaitableTimer(timer, &due, 0, NULL, NULL, FALSE))
      break;
    if (WaitForSingleObject(timer, 100) != WAIT_OBJECT_0)
      break;
    now = counter();
  }
}
void Dbaa_WindowClose(void) {
#ifdef DBAA_GAME_AUDIO_ENABLED
  if (game_task) {
    AvRevertMmThreadCharacteristics(game_task);
    game_task = NULL;
  }
#endif
  if (thread) {
    SetEvent(stop);
    WaitForSingleObject(thread, INFINITE);
    CloseHandle(thread);
    thread = NULL;
  }
  HANDLE *handles[] = {&timer, &ready, &stop, &submitted};
  for (unsigned i = 0; i < sizeof(handles) / sizeof(handles[0]); ++i)
    if (*handles[i]) {
      CloseHandle(*handles[i]);
      *handles[i] = NULL;
    }
}
