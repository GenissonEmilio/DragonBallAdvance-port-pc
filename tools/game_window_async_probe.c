/* Test only this process's hidden window, including a deliberately stalled
 * window thread. No hook is installed in another process. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "game_window.h"
#include <stdint.h>
#include <stdio.h>

static HANDLE entered, release, finished;
static LRESULT CALLBACK stall(int code, WPARAM w, LPARAM l) {
  if (code >= 0 && ((MSG *)l)->message == WM_APP + 42) {
    SetEvent(entered);
    WaitForSingleObject(release, 5000);
    SetEvent(finished);
  }
  return CallNextHookEx(NULL, code, w, l);
}
static int message(HWND window, UINT type, unsigned key) {
  DWORD_PTR result;
  return SendMessageTimeoutW(window, type, key, 0, SMTO_ABORTIFHUNG, 500, &result) != 0;
}
static int key(HWND window, unsigned code, int down, unsigned expected) {
  uint16_t value;
  return message(window, down ? WM_KEYDOWN : WM_KEYUP, code) &&
         !Dbaa_WindowPoll(&value) && value == expected;
}
int main(void) {
  if (Dbaa_WindowOpen()) return 1;
  HWND window = FindWindowW(L"DbaaNativeWindow", NULL);
  DWORD process;
  DWORD window_thread = GetWindowThreadProcessId(window, &process);
  int ok = window && process == GetCurrentProcessId() && window_thread != GetCurrentThreadId();
  const unsigned keys[10] = {'Z', 'X', VK_BACK, VK_RETURN, VK_RIGHT, VK_LEFT,
                              VK_UP, VK_DOWN, 'S', 'A'};
  for (unsigned i = 0; i < 10; ++i) {
    ok &= key(window, keys[i], 1, 1u << i);
    ok &= key(window, keys[i], 1, 1u << i);
    ok &= key(window, keys[i], 0, 0);
  }
  ok &= key(window, 'Z', 1, 1) && key(window, 'X', 1, 3);
  ok &= message(window, WM_KILLFOCUS, 0);
  uint16_t value;
  ok &= !Dbaa_WindowPoll(&value) && !value;
  entered = CreateEventW(NULL, TRUE, FALSE, NULL);
  release = CreateEventW(NULL, TRUE, FALSE, NULL);
  finished = CreateEventW(NULL, TRUE, FALSE, NULL);
  HHOOK hook = SetWindowsHookExW(WH_GETMESSAGE, stall, NULL, window_thread);
  ok &= hook && entered && release && finished;
  PostMessageW(window, WM_APP + 42, 0, 0);
  ok &= WaitForSingleObject(entered, 500) == WAIT_OBJECT_0;
  LARGE_INTEGER before, after, frequency;
  QueryPerformanceFrequency(&frequency);
  QueryPerformanceCounter(&before);
  static uint32_t pixels[240 * 160];
  for (unsigned i = 0; i < 100; ++i) {
    pixels[i] = i;
    Dbaa_WindowPresent(pixels);
    ok &= !Dbaa_WindowPoll(&value);
  }
  QueryPerformanceCounter(&after);
  double handoff = (double)(after.QuadPart - before.QuadPart) / frequency.QuadPart;
  int independent = WaitForSingleObject(finished, 0) == WAIT_TIMEOUT;
  ok &= independent;
  SetEvent(release);
  ok &= WaitForSingleObject(finished, 500) == WAIT_OBJECT_0;
  if (hook) UnhookWindowsHookEx(hook);
  CloseHandle(entered); CloseHandle(release); CloseHandle(finished);
  /* A deliberate window stall precedes pacing, so open a fresh frame clock. */
  Dbaa_WindowClose();
  ok &= Dbaa_WindowOpen() == 0;
  window = FindWindowW(L"DbaaNativeWindow", NULL);
  QueryPerformanceCounter(&before);
  for (unsigned i = 0; i < 120; ++i) {
    ok &= !Dbaa_WindowPoll(&value);
    Dbaa_WindowPace();
  }
  QueryPerformanceCounter(&after);
  double seconds = (double)(after.QuadPart - before.QuadPart) / frequency.QuadPart;
  double expected = 120.0 * 280896.0 / 16777216.0;
  ok &= seconds >= expected - 0.02 && seconds <= expected + 0.25;
  ok &= message(window, WM_CLOSE, 0);
  ok &= Dbaa_WindowPoll(&value) != 0;
  Dbaa_WindowClose();
  printf("{\"ok\":%s,\"keys_tested\":10,\"key_repeat\":true,\"focus_release\":true,"
         "\"close_and_reopen\":true,\"window_thread_distinct\":true,"
         "\"publisher_independent_of_stalled_ui\":%s,\"published_while_ui_blocked\":100,"
         "\"handoff_seconds\":%.9f,\"paced_frames\":120,\"seconds\":%.9f}\n",
         ok ? "true" : "false", independent ? "true" : "false", handoff, seconds);
  return ok ? 0 : 1;
}
