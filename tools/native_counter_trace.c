/* Test-only passive logging of game counter writes; values are unchanged. */
#include "gba/gba_runtime.h"
#include "game_runtime.h"
#include <stdio.h>
extern unsigned char *io_regs;
void Dbaa_UntracedWrite32(u32 address, u32 value);
void bus_write32(u32 address, u32 value) {
  unsigned frame = Dbaa_GameFrameCount();
  if (address == 0x030030D4 && frame <= 10)
    fprintf(stderr, "COUNTER frame=%u v=%u value=%u last_function=%08X\n", frame,
            io_regs[6] | (unsigned)io_regs[7] << 8, value,
            g_func_ring[(g_func_ring_i-1) & 4095]);
  Dbaa_UntracedWrite32(address, value);
}
