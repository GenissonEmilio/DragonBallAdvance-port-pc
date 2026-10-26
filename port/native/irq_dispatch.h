#ifndef DBAA_IRQ_DISPATCH_H
#define DBAA_IRQ_DISPATCH_H
#include "music_player.h"

typedef struct DbaaIrqSelection {
  uint32_t target, table_address, table_offset, acknowledged;
} DbaaIrqSelection;

/* Native counterpart of the ARM dispatcher copied from ROM 0x080000FC.
 * Return 1 for the original's permanent GamePak interrupt loop, else 0.
 * The caller tail-calls target with r0=target, r1=table_address,
 * r2=table_offset, r3=0x04000200 and N=C=0, Z=(acknowledged==0).
 * V and r4-r14 are unchanged. Not a new GBA C matching target. */
int Dbaa_IrqSelect(const DbaaMusicHost *, uint32_t copied_code,
                   DbaaIrqSelection *);
#endif
