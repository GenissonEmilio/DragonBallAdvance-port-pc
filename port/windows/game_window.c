/* Win32 presentation/input only; game rendering is performed by the software
 * PPU. The rational frame clock uses the GBA's 280896/16777216 second period.
 */
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

static HWND window;
static HANDLE timer;
static BITMAPINFO bitmap;
static uint32_t framebuffer[240 * 160];
static uint64_t origin, frequency, frames;
static int quit;
static uint16_t held_keys;

static uint16_t key_bit(WPARAM key) {
  static const int keys[10] = {'Z',     'X',   VK_BACK, VK_RETURN, VK_RIGHT,
                               VK_LEFT, VK_UP, VK_DOWN, 'S',       'A'};
  for (unsigned i = 0; i < 10; ++i)
    if (key == (WPARAM)keys[i])
      return (uint16_t)(1u << i);
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
    held_keys = 0;
    return 0;
  case WM_KEYDOWN:
    held_keys |= key_bit(w);
    return 0;
  case WM_KEYUP:
    held_keys &= (uint16_t)~key_bit(w);
    return 0;
  case WM_CLOSE:
    quit = 1;
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
int Dbaa_WindowOpen(void) {
  WNDCLASSW type = {0};
  type.lpfnWndProc = procedure;
  type.hInstance = GetModuleHandleW(NULL);
  type.hCursor = LoadCursorW(NULL, MAKEINTRESOURCEW(32512));
  type.lpszClassName = L"DbaaNativeWindow";
  if (!RegisterClassW(&type) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
    return -1;
  bitmap.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bitmap.bmiHeader.biWidth = 240;
  bitmap.bmiHeader.biHeight = -160;
  bitmap.bmiHeader.biPlanes = 1;
  bitmap.bmiHeader.biBitCount = 32;
  RECT size = {0, 0, 720, 480};
  AdjustWindowRect(&size, WS_OVERLAPPEDWINDOW, FALSE);
  window = CreateWindowW(type.lpszClassName,
                         L"Dragon Ball: Advanced Adventure | Setas: mover | "
                         L"Z/X: A/B | Enter: Start",
                         WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT,
                         size.right - size.left, size.bottom - size.top, NULL,
                         NULL, type.hInstance, NULL);
  if (!window)
    return -1;
  timer = CreateWaitableTimerExW(NULL, NULL, 2, TIMER_ALL_ACCESS);
  if (!timer)
    timer = CreateWaitableTimerExW(NULL, NULL, 0, TIMER_ALL_ACCESS);
  if (!timer) {
    Dbaa_WindowClose();
    return -1;
  }
  LARGE_INTEGER q;
  QueryPerformanceFrequency(&q);
  frequency = (uint64_t)q.QuadPart;
  origin = counter();
#ifdef DBAA_GAME_AUDIO_ENABLED
  /* The producer must meet the audio deadlines too. MMCSS gives the game
   * thread a bounded multimedia priority while the separate render worker
   * retains its higher Pro Audio category. */
  DWORD task_index = 0;
  game_task = AvSetMmThreadCharacteristicsW(L"Games", &task_index);
  if (game_task)
    AvSetMmThreadPriority(game_task, AVRT_PRIORITY_HIGH);
  fprintf(stderr, "[window] Games MMCSS %s\n", game_task ? "active" : "unavailable");
#endif
#ifdef DBAA_WINDOW_TEST
  ShowWindow(window, SW_HIDE);
#else
  ShowWindow(window, SW_SHOW);
#endif
  return 0;
}
void Dbaa_WindowPresent(const uint32_t *pixels) {
  memcpy(framebuffer, pixels, sizeof(framebuffer));
  HDC dc = GetDC(window);
  paint(dc);
  ReleaseDC(window, dc);
}
int Dbaa_WindowPoll(uint16_t *pressed) {
  MSG message;
  while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
    if (message.message == WM_QUIT)
      quit = 1;
    TranslateMessage(&message);
    DispatchMessageW(&message);
  }
  *pressed = held_keys;
  return quit;
}
void Dbaa_WindowPace(void) {
  uint64_t deadline = origin + Dbaa_AudioDeadline(++frames, frequency);
  uint64_t now = counter();
#ifdef DBAA_GAME_AUDIO_ENABLED
  size_t queued;
  if (Dbaa_GameAudioQueueDepth(&queued)) {
    /* Keep the byte stream unchanged. Correct the frame clock towards the
     * device's consumption rate, and refill promptly after scheduling stalls.
     * The endpoint has its own additional buffer (roughly 50 ms). */
    if (queued < 3600) {
      origin = now - Dbaa_AudioDeadline(frames, frequency);
      return;
    }
    int64_t error = (int64_t)queued - 4800;
    int64_t correction = error * (int64_t)frequency / (48000 * 32);
    int64_t limit = (int64_t)frequency / 1000;
    if (correction < -limit)
      correction = -limit;
    if (correction > limit)
      correction = limit;
    origin = (uint64_t)((int64_t)origin + correction);
    deadline = (uint64_t)((int64_t)deadline + correction);
  }
#endif
  /* A debugger pause/suspend must not trigger a long burst of catch-up frames.
   */
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
    DWORD result =
        MsgWaitForMultipleObjects(1, &timer, FALSE, 100, QS_ALLINPUT);
    if (result != WAIT_OBJECT_0)
      break; /* Let the next polling boundary handle queued window messages. */
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
  if (timer) {
    CloseHandle(timer);
    timer = NULL;
  }
  if (window) {
    DestroyWindow(window);
    window = NULL;
  }
}
