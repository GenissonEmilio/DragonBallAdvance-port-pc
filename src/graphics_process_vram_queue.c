#include "graphics.h"

struct DbaaVramTransfer
{
    DbaaU32 source;
    DbaaU32 destination;
    DbaaU16 size;
    DbaaU16 unknown0A;
};
extern DbaaU8 gVramQueueReadIndex;
extern DbaaU8 gVramQueueWriteIndex;
extern struct DbaaVramTransfer gVramTransferQueue[];

int Graphics_ProcessVramQueue(void)
{
    while (gVramQueueReadIndex != gVramQueueWriteIndex)
    {
        struct DbaaVramTransfer *entry = &gVramTransferQueue[gVramQueueReadIndex];
        if (entry->size != 0)
        {
            DbaaU32 offset;
            for (offset = 0; entry->size != 0; offset += 0x400)
            {
                if (entry->size > 0x400)
                {
                    DMA_START(entry->source + offset, entry->destination + offset, 0x80000200);
                    entry->size -= 0x400;
                }
                else
                {
                    DMA_START(entry->source + offset, entry->destination + offset,
                              0x80000000 | (entry->size >> 1));
                    entry->size = 0;
                }
            }
        }
        gVramQueueReadIndex = (gVramQueueReadIndex + 1) & 0x7F;
        if ((REG_DISPSTAT & 1) == 0)
            return 0;
    }
    return 1;
}
