/* Actual runtime DMA3/EEPROM protocol. No guest function executes. */
#include "gba/gba_runtime.h"
#include "gba/display.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned address_bits, blocks;
static unsigned long long busy_polls;
static unsigned payload(unsigned offset) {
  return (offset * 73u + ((offset >> 3) ^ 0xA5u) * 19u + 0x37u) & 255u;
}
static void dma_to_eeprom(const unsigned *bits, unsigned count) {
  for (unsigned i = 0; i < count; ++i)
    bus_write16(0x02010000 + 2*i, bits[i] & 1);
  bus_write32(0x040000D4, 0x02010000);
  bus_write32(0x040000D8, 0x0D000000);
  bus_write32(0x040000DC, 0x80400000 | count);
}
static unsigned command(unsigned *bits, unsigned block, int writing) {
  unsigned n = 0;
  bits[n++] = 1;
  bits[n++] = !writing;
  for (int i = (int)address_bits - 1; i >= 0; --i)
    bits[n++] = (block >> i) & 1;
  return n;
}
static int write_block(unsigned block) {
  unsigned bits[81], n = command(bits, block, 1);
  for (unsigned i = 0; i < 8; ++i) {
    unsigned value = payload(block * 8 + i);
    for (int shift = 7; shift >= 0; --shift)
      bits[n++] = (value >> shift) & 1;
  }
  bits[n++] = 0;
  dma_to_eeprom(bits, n);
  /* The original SDK polls the ready bit after DMA completes. */
  if (bus_read16(0x0D000000) & 1)
    return 0;
  unsigned polls = 0;
  while (!(bus_read16(0x0D000000) & 1))
    if (++polls > 1000000)
      return 0;
  busy_polls += polls;
  return 1;
}
static int read_block(unsigned block, int erased) {
  unsigned bits[17], n = command(bits, block, 0);
  bits[n++] = 0;
  dma_to_eeprom(bits, n);
  bus_write32(0x040000D4, 0x0D000000);
  bus_write32(0x040000D8, 0x02011000);
  bus_write32(0x040000DC, 0x81000000 | 68);
  for (unsigned i = 0; i < 4; ++i)
    if (bus_read16(0x02011000 + 2*i) & 1)
      return 0;
  for (unsigned i = 0; i < 8; ++i) {
    unsigned value = 0;
    for (unsigned j = 0; j < 8; ++j)
      value = (value << 1) | (bus_read16(0x02011008 + 2*(8*i+j)) & 1);
    if (value != (erased ? 255 : payload(block * 8 + i)))
      return 0;
  }
  return 1;
}
int main(int argc, char **argv) {
  if (argc != 4 || (strcmp(argv[1], "write") && strcmp(argv[1], "read")))
    return 2;
  unsigned capacity = (unsigned)atoi(argv[2]);
  if (capacity != 4 && capacity != 64)
    return 2;
  address_bits = capacity == 4 ? 6 : 14;
  blocks = capacity == 4 ? 64 : 1024;
  char *display_args[] = {argv[0], argv[3], "--headless"};
  display_parse_args(3, display_args);
  gba_init(argv[3]);
  int writing = !strcmp(argv[1], "write"), ok = 1;
  if (writing) {
    ok = read_block(0, 1) && read_block(blocks - 1, 1);
    for (unsigned block = 0; ok && block < blocks; ++block)
      ok = write_block(block);
  }
  for (unsigned block = 0; ok && block < blocks; ++block)
    ok = read_block(block, 0);
  gba_shutdown();
  printf("{\"ok\":%s,\"mode\":\"%s\",\"capacity_kbit\":%u,\"blocks\":%u,"
         "\"busy_polls\":%llu,\"game_save_round_trip_validated\":false,"
         "\"cycle_exact_busy_timing_validated\":false}\n",
         ok ? "true" : "false", argv[1], capacity, blocks, busy_polls);
  return ok ? 0 : 1;
}
