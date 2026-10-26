/* Exercise only this process's hidden Win32 window and real message pump. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "game_window.h"
#include <stdio.h>

static int check_keys(HWND window, unsigned key, int down, unsigned expected) {
  PostMessageW(window, down ? WM_KEYDOWN : WM_KEYUP, key, 0);
  uint16_t value;
  return !Dbaa_WindowPoll(&value) && value == expected;
}
int main(void) {
  if (Dbaa_WindowOpen()) return 1;
  HWND window = FindWindowW(L"DbaaNativeWindow", NULL);
  DWORD process;
  GetWindowThreadProcessId(window, &process);
  if (!window || process != GetCurrentProcessId()) return 1;
  const unsigned keys[10] = {'Z', 'X', VK_BACK, VK_RETURN, VK_RIGHT, VK_LEFT,
                              VK_UP, VK_DOWN, 'S', 'A'};
  int ok = 1;
  for (unsigned i = 0; i < 10; ++i) {
    ok &= check_keys(window, keys[i], 1, 1u << i);
    ok &= check_keys(window, keys[i], 1, 1u << i); /* key repeat */
    ok &= check_keys(window, keys[i], 0, 0);
  }
  ok &= check_keys(window, 'Z', 1, 1);
  ok &= check_keys(window, 'X', 1, 3);
  ok &= check_keys(window, VK_RIGHT, 1, 0x13);
  ok &= check_keys(window, 'Z', 0, 0x12);
  PostMessageW(window, WM_KILLFOCUS, 0, 0);
  uint16_t value;
  ok &= !Dbaa_WindowPoll(&value) && !value;
  LARGE_INTEGER before, after, frequency;
  QueryPerformanceFrequency(&frequency);
  QueryPerformanceCounter(&before);
  for (unsigned i = 0; i < 120; ++i) {
    ok &= !Dbaa_WindowPoll(&value);
    Dbaa_WindowPace();
  }
  QueryPerformanceCounter(&after);
  double seconds = (double)(after.QuadPart - before.QuadPart) / frequency.QuadPart;
  double expected = 120.0 * 280896.0 / 16777216.0;
  ok &= seconds >= expected - 0.02 && seconds <= expected + 0.25;
  PostMessageW(window, WM_CLOSE, 0, 0);
  ok &= Dbaa_WindowPoll(&value) != 0;
  Dbaa_WindowClose();
  printf("{\"ok\":%s,\"keys_tested\":10,\"key_repeat\":true,"
         "\"focus_release\":true,\"close\":true,\"paced_frames\":120,"
         "\"seconds\":%.9f,\"expected_seconds\":%.9f}\n",
         ok ? "true" : "false", seconds, expected);
  return ok ? 0 : 1;
}
