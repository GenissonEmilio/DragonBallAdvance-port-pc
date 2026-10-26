#include "irq_dispatch.h"

int Dbaa_IrqSelect(const DbaaMusicHost *host, uint32_t copied_code,
                   DbaaIrqSelection *result) {
  static const uint16_t priority[] = {0x00C0, 0x0001, 0x0002, 0x0004, 0x0008,
                                      0x0010, 0x0020, 0x0100, 0x0200, 0x0400,
                                      0x0800, 0x1000, 0x2000};
  uint32_t word = host->read(host->user, 0x04000200, 4);
  uint32_t pending = word & (word >> 16);
  if (pending & 0x2000u)
    return 1;
  unsigned index = 0;
  uint32_t mask;
  do {
    mask = pending & priority[index];
    if (mask || index == 12)
      break;
    ++index;
  } while (1);
  host->write(host->user, 0x04000202, mask, 2);
  result->table_offset = index * 4u;
  result->table_address =
      host->read(host->user, copied_code + 0xCC, 4) + result->table_offset;
  result->target = host->read(host->user, result->table_address, 4);
  result->acknowledged = mask;
  return 0;
}
