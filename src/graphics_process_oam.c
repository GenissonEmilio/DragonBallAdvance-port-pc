#include "graphics.h"

struct DbaaOamEntry
{
    DbaaU16 attr0, attr1, attr2;
    DbaaS8 next;
    DbaaU8 unknown07;
};

extern DbaaS8 gOamOrderHeads[];
extern DbaaS8 gOamOrderTails[];
extern DbaaU8 gOamCopiedOrder[];
extern DbaaU8 gOamPausedStartIndex;
extern DbaaU8 gOamFreeIndex;
extern struct DbaaOamEntry gOamEntries[];
extern struct DbaaOamEntry gOamAllocatedEntries[];

void Graphics_ProcessOam(void)
{
    struct DbaaOamEntry *target = &gOamEntries[0];
    DbaaU8 outputIndex = 0;
    int i;

    for (i = 0; i < 32; i++)
    {
        DbaaS8 index = gOamOrderHeads[i];
        while (index != -1)
        {
            struct DbaaOamEntry *source = gOamAllocatedEntries + index;
            DMA_START(source, target, 0x80000003);
            target++;
            gOamCopiedOrder[index] = outputIndex++;
            index = source->next;
        }
    }
    if (gSystemFlags & 0x800)
    {
        i = gOamFreeIndex;
        target = gOamEntries + i;
        for (; i < gOamPausedStartIndex; i++)
        {
            DMA_FILL16(0x200, target, 0x81000003);
            target++;
        }
    }
    else if (gSystemFlags & 0x400)
    {
        i = gOamFreeIndex - 1;
        target = gOamEntries + i;
        {
            int readBack = 0;
            int writeBack = 0;
            for (; i >= 0;)
            {
                int bytes = 6;
                DMA_START(target - readBack, &gOamEntries[127 - writeBack], 0x80000000 | (bytes / 2));
                readBack++;
                i--;
                writeBack++;
            }
        }
        gOamPausedStartIndex = 128 - gOamFreeIndex;
        for (i = 0; i < gOamPausedStartIndex; i++)
        {
            DMA_FILL16(0x200, gOamEntries + i, 0x81000003);
            /* Keep this induction variable: no instructions are emitted. */
            __asm__("" : : "r"(i));
        }
    }
    else
        gOamPausedStartIndex = 0;
    gOamFreeIndex = 0;
    if (gSystemFlags & 0x4000)
    {
        {
            volatile DbaaU32 fill = ~0;
            Bios_CpuSet((const void *)&fill, gOamOrderHeads, 0x05000008);
        }
        {
            volatile DbaaU32 fill = ~0;
            Bios_CpuSet((const void *)&fill, gOamOrderTails, 0x05000008);
        }
    }
    else
    {
        DMA_FILL32(~0, gOamOrderHeads, 0x85000008);
        DMA_FILL32(~0, gOamOrderTails, 0x85000008);
    }
}
