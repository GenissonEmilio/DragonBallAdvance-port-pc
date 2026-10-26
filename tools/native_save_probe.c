/* Exercise the actual native runtime's EEPROM bus and disk persistence. No
 * translated game function is executed. Run only on the verifier's sandbox. */
#include "gba/gba_runtime.h"
#include "gba/display.h"
#include <stdio.h>
#include <string.h>

static unsigned payload(unsigned offset) {
  return (offset * 73u + ((offset >> 3) ^ 0xA5u) * 19u + 0x37u) & 255u;
}
static void bit(unsigned value) { bus_write16(0x0D000000, value & 1); }
static void address(unsigned block) {
  for (int i = 13; i >= 0; --i)
    bit(block >> i);
}
static void write_block(unsigned block) {
  bit(1);
  bit(0);
  address(block);
  for (unsigned i = 0; i < 8; ++i) {
    unsigned value = payload(block * 8 + i);
    for (int shift = 7; shift >= 0; --shift)
      bit(value >> shift);
  }
  bit(0);
}
static int read_block(unsigned block) {
  bit(1);
  bit(1);
  address(block);
  bit(0);
  for (unsigned i = 0; i < 4; ++i)
    if (bus_read16(0x0D000000) & 1)
      return 0;
  for (unsigned i = 0; i < 8; ++i) {
    unsigned value = 0;
    for (unsigned j = 0; j < 8; ++j)
      value = (value << 1) | (bus_read16(0x0D000000) & 1);
    if (value != payload(block * 8 + i))
      return 0;
  }
  return 1;
}
int main(int argc, char **argv) {
  if (argc != 3 || (strcmp(argv[1], "write") && strcmp(argv[1], "read")))
    return 2;
  char *display_args[] = {argv[0], argv[2], "--headless"};
  display_parse_args(3, display_args);
  gba_init(argv[2]);
  int writing = !strcmp(argv[1], "write");
  if (writing)
    for (unsigned block = 0; block < 1024; ++block)
      write_block(block);
  int ok = 1;
  for (unsigned block = 0; block < 1024; ++block)
    if (!read_block(block)) {
      fprintf(stderr, "EEPROM block mismatch: %u\n", block);
      ok = 0;
      break;
    }
  gba_shutdown();
  printf("{\"ok\":%s,\"mode\":\"%s\",\"blocks\":1024,"
         "\"game_save_round_trip_validated\":false,"
         "\"busy_timing_validated\":false,\"hardware_erased_value_validated\":false}\n",
         ok ? "true" : "false", argv[1]);
  return ok ? 0 : 1;
}
