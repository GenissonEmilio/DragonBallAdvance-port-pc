/* Hardware scheduler probe: no guest instructions, tasks or callbacks execute. */
#include "gba/gba_runtime.h"
#include "gba/display.h"
#include "game_runtime.h"
#include <stdio.h>
#include <stdlib.h>
static void next_frame(void) {
  unsigned frame = Dbaa_GameFrameCount();
  while (Dbaa_GameFrameCount() == frame) cpu_fetches(1);
}
int main(int n, char **v) {
  if (n != 3) return 2;
  char *args[] = {v[0], v[1], "--headless"};
  display_parse_args(3, args);
  gba_init(v[1]);
  unsigned mode = (unsigned)strtoul(v[2], NULL, 10);
  bus_write16(0x04000200, 0);
  bus_write16(0x04000208, 0);
  bus_write16(0x04000202, 0xFFFF);
  bus_write16(0x04000004, (127u << 8) | ((mode < 8 ? mode : 0) << 3));
  next_frame();
  unsigned first = bus_read16(0x04000202) & 7u, late = 0, next = 0, disabled = 0;
  if (mode == 8) {
    bus_write16(0x04000202, 0xFFFF);
    bus_write16(0x04000004, (127u << 8) | 8);
    for (unsigned i = 0; i < 5; ++i) cpu_fetches(1);
    late = bus_read16(0x04000202) & 7u;
    next_frame();
    next = bus_read16(0x04000202) & 7u;
    bus_write16(0x04000004, 127u << 8);
    bus_write16(0x04000202, 0xFFFF);
    next_frame();
    disabled = bus_read16(0x04000202) & 7u;
  }
  if (mode == 9 || mode == 10) {
    if (mode == 10) for (unsigned i = 0; i < 367; ++i) cpu_fetches(1);
    first = bus_read16(0x04000004);
    bus_write16(0x04000004, 0xFF00);
    late = bus_read16(0x04000004);
    bus_write16(0x04000004, 0x7FFF);
    next = bus_read16(0x04000004);
  }
  if (mode == 11) {
    bus_write16(0x04000202, 0xFFFF);
    bus_write16(0x04000004, (160u << 8) | 0x20);
    first = bus_read16(0x04000004);
    late = bus_read16(0x04000202) & 7u;
    bus_write16(0x04000202, 0xFFFF);
    bus_write16(0x04000004, (160u << 8) | 0x20);
    next = bus_read16(0x04000202) & 7u;
    bus_write16(0x04000004, (161u << 8) | 0x20);
    bus_write16(0x04000004, (160u << 8) | 0x20);
    disabled = bus_read16(0x04000202) & 7u;
  }
  if (mode == 12) {
    while (bus_read16(0x04000006) != 227) cpu_fetches(1);
    first = bus_read16(0x04000004) & 7u;
    while (bus_read16(0x04000006) != 0) cpu_fetches(1);
    late = bus_read16(0x04000004) & 7u;
  }
  if (mode == 13) {
    first = bus_read16(0x04000006);
    bus_write16(0x04000006, 37);
    late = bus_read16(0x04000006);
  }
  gba_shutdown();
  printf("%u %u %u %u %u\n", mode, first, late, next, disabled);
  return 0;
}
