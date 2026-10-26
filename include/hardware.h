#ifndef DBAA_HARDWARE_H
#define DBAA_HARDWARE_H

#include "game_state.h"

#define IO16(address) (*(volatile DbaaU16 *)(address))
#define IO32(address) (*(volatile DbaaU32 *)(address))

struct DbaaDmaRegisters
{
    const void *source;
    void *destination;
    DbaaU32 control;
};

#define DMA3 (*(volatile struct DbaaDmaRegisters *)0x040000D4)
/* Plain compound scopes retain agbcc's original allocation and loop layout.
 * Use these macros inside explicit if/else braces. Fill starts a transfer;
 * explicit waits are retained where they occur in the original ROM.
 */
#define DMA_START(source_, destination_, control_) \
    { \
        volatile DbaaU32 *dma = (volatile DbaaU32 *)0x040000D4; \
        dma[0] = (DbaaU32)(source_); \
        dma[1] = (DbaaU32)(destination_); \
        dma[2] = (control_); \
        (void)dma[2]; \
    }
#define DMA_WAIT() \
    { \
        volatile DbaaU32 *dma = (volatile DbaaU32 *)0x040000D4; \
        while (dma[2] & 0x80000000) ; \
    }
#define DMA_FILL32(value_, destination_, control_) \
    { \
        volatile DbaaU32 fill = (value_); \
        DMA_START(&fill, (destination_), (control_)); \
    }
#define DMA_FILL16(value_, destination_, control_) \
    { \
        volatile DbaaU16 fill = (value_); \
        DMA_START(&fill, (destination_), (control_)); \
    }

#endif
