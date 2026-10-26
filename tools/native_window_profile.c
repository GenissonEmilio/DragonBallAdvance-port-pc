/* Test-only timing wrapper. Store observations in RAM; write after exit.
 * Compile game_window.c with the corresponding three symbols renamed.
 * No PCM, clock, input, game state or rendering work is changed. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "game_window.h"

void dbaa_profile_original_present(const uint32_t *pixels);
int dbaa_profile_original_poll(uint16_t *pressed);
void dbaa_profile_original_pace(void);

struct Row {
  uint64_t work_wall, work_cpu, present_wall, present_cpu;
  uint64_t poll_wall, poll_cpu, pace_wall, pace_cpu, read_bytes, write_bytes;
};
static struct Row rows[60000];
static unsigned count;
static uint64_t frequency, last_wall, last_cpu, last_read, last_write;
static int started;

static uint64_t wall(void) {
  LARGE_INTEGER n;
  QueryPerformanceCounter(&n);
  return (uint64_t)n.QuadPart;
}
static uint64_t cpu(void) {
  FILETIME start, end, kernel, user;
  if (!GetThreadTimes(GetCurrentThread(), &start, &end, &kernel, &user))
    return 0;
  ULARGE_INTEGER k, u;
  k.LowPart = kernel.dwLowDateTime; k.HighPart = kernel.dwHighDateTime;
  u.LowPart = user.dwLowDateTime; u.HighPart = user.dwHighDateTime;
  return k.QuadPart + u.QuadPart;
}
static void finish(void) {
  const char *name = getenv("DBAA_FRAME_PROFILE");
  FILE *file = fopen(name ? name : "frame_profile.csv", "wb");
  if (!file)
    return;
  fprintf(file, "frame,work_us,work_cpu_us,present_us,present_cpu_us,poll_us,poll_cpu_us,pace_us,pace_cpu_us,read_bytes,write_bytes\n");
  for (unsigned i = 0; i < count; ++i) {
    struct Row *r = &rows[i];
    fprintf(file, "%u,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu\n", i + 1,
            (unsigned long long)(r->work_wall * 1000000 / frequency), (unsigned long long)(r->work_cpu / 10),
            (unsigned long long)(r->present_wall * 1000000 / frequency), (unsigned long long)(r->present_cpu / 10),
            (unsigned long long)(r->poll_wall * 1000000 / frequency), (unsigned long long)(r->poll_cpu / 10),
            (unsigned long long)(r->pace_wall * 1000000 / frequency), (unsigned long long)(r->pace_cpu / 10),
            (unsigned long long)r->read_bytes, (unsigned long long)r->write_bytes);
  }
  fclose(file);
}
static void init(void) {
  if (started)
    return;
  LARGE_INTEGER n;
  QueryPerformanceFrequency(&n);
  frequency = (uint64_t)n.QuadPart;
  last_wall = wall(); last_cpu = cpu();
  atexit(finish);
  started = 1;
}
void Dbaa_WindowPresent(const uint32_t *pixels) {
  init();
  uint64_t w = wall(), c = cpu();
  dbaa_profile_original_present(pixels);
  if (count < 60000) {
    rows[count].present_wall += wall() - w;
    rows[count].present_cpu += cpu() - c;
  }
}
int Dbaa_WindowPoll(uint16_t *pressed) {
  init();
  uint64_t w = wall(), c = cpu();
  int result = dbaa_profile_original_poll(pressed);
  if (count < 60000) {
    rows[count].poll_wall += wall() - w;
    rows[count].poll_cpu += cpu() - c;
  }
  return result;
}
void Dbaa_WindowPace(void) {
  init();
  uint64_t w = wall(), c = cpu();
  if (count < 60000) {
    rows[count].work_wall = w - last_wall;
    rows[count].work_cpu = c - last_cpu;
    IO_COUNTERS io;
    if (GetProcessIoCounters(GetCurrentProcess(), &io)) {
      rows[count].read_bytes = io.ReadTransferCount - last_read;
      rows[count].write_bytes = io.WriteTransferCount - last_write;
      last_read = io.ReadTransferCount; last_write = io.WriteTransferCount;
    }
  }
  dbaa_profile_original_pace();
  last_wall = wall(); last_cpu = cpu();
  if (count < 60000) {
    rows[count].pace_wall = last_wall - w;
    rows[count].pace_cpu = last_cpu - c;
    ++count;
  }
}
