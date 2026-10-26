/* Algorithm reference only; not part of the matching build.
 * Exact register-flow reconstruction: src/graphics_process_background_queue.c.
 */
/* NONMATCHING study candidate. Algorithm reference: SAT-R/sa2 src/background.c,
 * revision 393357f7c9d46b5c10b6c41a57b80fe3b58f3c8d. Compare against DBAA USA. */
#include "backgrounds.h"
#define u8 DbaaU8
#define u16 DbaaU16
#define u32 DbaaU32
#define s16 DbaaS16
#define s32 int
#define Background struct DbaaBackground
#define FALSE 0
#define TRUE 1
#define PORTABLE 0
#define RENDERER 1
#define RENDERER_OPENGL 2
#define WIDESCREEN_HACK 0
#define CastPointer(p,i) ((void *)((DbaaU8 *)(p)+(i)))
#define ARRAY_COUNT(a) (sizeof(a)/sizeof((a)[0]))
#define REG_VCOUNT IO16(0x04000006)
#define DISPSTAT_VBLANK 1
#define DISPCNT_MODE_1 1
#define DISPCNT_MODE_2 2
#define DISPCNT_MODE_0 0
#define BACKGROUND_FLAGS_MASK_BG_ID 3
#define BACKGROUND_FLAG_20 0x20
#define BACKGROUND_FLAG_IS_LEVEL_MAP 0x40
#define BACKGROUND_FLAG_80 0x80
#define BACKGROUND_FLAG_100 0x100
#define TileMask_FlipXY 0xc00
#define TileMask_FlipX 0x400
#define TileMask_FlipY 0x800
#define gBackgroundsCopyQueueCursor gBackgroundReadIndex
#define gBackgroundsCopyQueueIndex gBackgroundWriteIndex
#define gBackgroundsCopyQueue gBackgroundQueue
#define gDispCnt gDisplayControlShadow
#define gBgCntRegs gBgControlShadow
#define gBgScrollRegs gBackgroundScroll
#define Div Bios_Div
#define DmaCopy16(channel,source,destination,size) DMA_START((source),(destination),0x80000000|((int)(size)/2))
int Graphics_ProcessBackgroundQueue(void)
{
    u16 sp00;
    s32 sp04 = 0;
    s32 bytesPerTileIndex;
    u16 sp0C; 
    u16 sp10;
    u16 sp14;
    u32 affine; 
    u32 bgId; 
    s32 sb;
    u32 dmaSize;
    s32 i;
    s32 j;
    u16 k;
#if (RENDERER == RENDERER_OPENGL)
    Platform_ProcessBackgroundsCopyQueue();
    return TRUE;
#endif
    while (gBackgroundsCopyQueueCursor != gBackgroundsCopyQueueIndex) {
        Background *bg;
#if !PORTABLE
        if (!(REG_DISPSTAT & DISPSTAT_VBLANK))
            return FALSE;
#endif
        REG_VCOUNT;
        {
            Background **backgrounds = &gBackgroundsCopyQueue[0];
            s32 index = gBackgroundsCopyQueueCursor;
            bg = backgrounds[index];
            gBackgroundsCopyQueueCursor = (gBackgroundsCopyQueueCursor + 1) % ARRAY_COUNT(gBackgroundsCopyQueue);
            if ((bg->flags & BACKGROUND_FLAG_20) && (bg->scrollX == bg->prevScrollX) && bg->scrollY == bg->prevScrollY)
                continue;
        }
        sp00 = bg->xTiles;
        bgId = (bg->flags & BACKGROUND_FLAGS_MASK_BG_ID);
        if (bgId >= 2 && (gDispCnt & (DISPCNT_MODE_1 | DISPCNT_MODE_2)) > DISPCNT_MODE_0) {
            affine = (gBgCntRegs[bgId] >> 14);
            sp0C = (0x10 << affine);
            bytesPerTileIndex = 1;
        } else {
#if WIDESCREEN_HACK
            if (bg->flags & BACKGROUND_FLAG_IS_LEVEL_MAP) {
                if (gBgCntRegs[bgId] & BGCNT_TXT512x256) {
                    sp0C = 64;
                } else {
                    sp0C = 32;
                }
            } else {
                sp0C = 32;
            }
#else
            sp0C = 32;
#endif
            affine = (gBgCntRegs[bgId] >> 14);
            if ((affine == 1) || (affine == 3)) {
#if NON_MATCHING
                sp0C = 64;
#endif
                sp04 = 0x800;
            }
            bytesPerTileIndex = 2;
        }
        sp0C = (u16)(sp0C * bytesPerTileIndex);
        if (!(bg->flags & BACKGROUND_FLAG_20)) {
            if (!(bg->flags & BACKGROUND_FLAG_IS_LEVEL_MAP)) {
                u8 *r1 = CastPointer(bg->layoutVram, bg->unk24 * sp0C);
                u16 *r7 = CastPointer(r1, bg->unk22 * bytesPerTileIndex);
                u16 r5 = bg->targetTilesY;
                u16 k;
                if (bg->flags & BACKGROUND_FLAG_100) {
                    if (bg->flags & BACKGROUND_FLAG_80) {
                        u32 r0Index = (((bg->unk20 + r5) - 1) * sp00) * bytesPerTileIndex;
                        void *r2Ptr = CastPointer(bg->layout, r0Index);
                        u16 *r4Ptr = CastPointer(r2Ptr, ((bg->unk1E + bg->targetTilesX) - 1) * bytesPerTileIndex);
                        while (r5-- != 0) {
                            for (k = 0; k < bg->targetTilesX; k++) {
                                r7[k] = (*(r4Ptr - k) ^ TileMask_FlipXY);
                            }
                            r7 = CastPointer(r7, sp0C);
                            r4Ptr = (void *)(((u8 *)r4Ptr) - (sp00 * bytesPerTileIndex));
                        }
                    } else {
                        u32 someIndex = (bg->unk20 * sp00);
                        void *r2Ptr = CastPointer(bg->layout, someIndex * bytesPerTileIndex);
                        u32 index2 = ((bg->unk1E + bg->targetTilesX) - 1);
                        u16 *r4Ptr = CastPointer(r2Ptr, index2 * bytesPerTileIndex);
                        while (r5-- != 0) {
                            for (k = 0; k < bg->targetTilesX; k++) {
                                r7[k] = (*(r4Ptr - k) ^ TileMask_FlipX);
                            }
                            r7 = CastPointer(r7, sp0C);
                            r4Ptr = CastPointer(r4Ptr, (sp00 * bytesPerTileIndex));
                        }
                    }
                } else {
                    u16 *r4Ptr;
                    if (bg->flags & BACKGROUND_FLAG_80) {
                        u32 r0Index = (((bg->unk20 + r5) - 1) * sp00);
                        void *r1Ptr = CastPointer(bg->layout, r0Index * bytesPerTileIndex);
                        r4Ptr = CastPointer(r1Ptr, bg->unk1E * bytesPerTileIndex);
                        while (r5-- != 0) {
                            u16 i;
                            sb = sp00 * bytesPerTileIndex;
                            for (i = 0; i < bg->targetTilesX; i++) {
                                r7[i] = r4Ptr[i] ^ 0x800;
                            }
                            r7 = CastPointer(r7, sp0C);
                            r4Ptr = (u16 *)(((u8 *)r4Ptr) - sb);
                        }
                    } else {
#ifndef NON_MATCHING
                        if ((affine & 1) && (bytesPerTileIndex == 2) && ((32 - bg->unk22) > 0)
                            && ((bg->targetTilesX + bg->unk22 - 32) > 0)) {
                            s32 vR2;
                            r4Ptr = (u16 *)(&bg->layout[bg->unk20 * sp00] + bg->unk1E);
                            sb = (32 - bg->unk22) * 2;
                            vR2 = (bg->targetTilesX + bg->unk22 - 32) * 2;
                            while (r5-- != 0) {
                                DmaCopy16(3, r4Ptr, r7, sb);
                                DmaCopy16(3, CastPointer(r4Ptr, sb), CastPointer(r7, sp04), vR2);
                                r7 = CastPointer(r7, sp0C);
                                r4Ptr = CastPointer(r4Ptr, (sp00 * bytesPerTileIndex));
                            }
                        } else
#endif
                        {
                            u32 r0Index = bg->unk20 * sp00 * bytesPerTileIndex;
                            void *r1Ptr = CastPointer(bg->layout, r0Index);
                            void *r4Ptr = CastPointer(r1Ptr, bg->unk1E * bytesPerTileIndex);
                            while (r5-- != 0) {
                                DmaCopy16(3, r4Ptr, r7, (s32)(bg->targetTilesX * bytesPerTileIndex));
                                r7 = CastPointer(r7, sp0C);
                                r4Ptr = CastPointer(r4Ptr, sp00 * bytesPerTileIndex);
                            }
                        }
                    }
                }
            } else {
                s32 sp18;
                s32 sp1C;
                u32 sp20;
                s32 r1;
                sp10 = bg->unk1E;
                sp14 = bg->unk20;
                for (i = 0; i < bg->targetTilesX; i += r1) {
                    s32 r5Res;
                    s32 r8;
                    s32 sp10_i = sp10 + i;
                    s32 temp;
                    sp18 = Div(sp10_i, bg->xTiles);
                    r1 = bg->xTiles;
                    r5Res = sp18;
                    sp1C = sp10_i - r5Res * bg->xTiles;
                    r8 = bg->targetTilesY;
                    temp = (bg->targetTilesX - i);
                    r1 -= sp1C;
                    if (r1 > temp)
                        r1 = (bg->targetTilesX - i);
                    sp20 = r1 * bytesPerTileIndex;
                    for (j = 0; j < bg->targetTilesY;) {
                        void *dmaSrc, *dmaDest;
                        s32 r5;
#ifndef NON_MATCHING
                        const u16 *r1Ptr;
                        void *r2Ptr;
                        void *r0Ptr;
#else
                        const u16 *r1Ptr;
                        void *r2Ptr;
                        void *r0Ptr;
#endif
                        s32 temp2;
                        u32 v;
                        s32 r4 = sp14 + j;
                        s32 result = Div(r4, bg->yTiles);
                        r4 -= result * bg->yTiles;
                        r5 = bg->yTiles - r4;
                        result *= bg->mapWidth;
                        r2Ptr = (void *)bg->metatileMap;
                        temp2 = sp18 << 1;
                        r0Ptr = CastPointer(r2Ptr, result * 2);
                        r1Ptr = CastPointer(r0Ptr, temp2);
                        v = *((u16 *)r1Ptr) * bg->xTiles * bg->yTiles;
                        v += r4 * bg->xTiles + sp1C;
                        v *= bytesPerTileIndex;
                        dmaSrc = ((u8 *)bg->layout) + v;
                        {
                            void *r0;
                            r0 = CastPointer(bg->layoutVram, bg->unk24);
                            r0 = CastPointer(r0, sp0C * j);
                            r0 = CastPointer(r0, bg->unk22);
                            dmaDest = CastPointer(r0, i * bytesPerTileIndex);
                        }
                        j += r5;
                        if (r5 > r8)
                            r5 = r8;
                        r8 -= r5;
                        while (r5-- != 0) {
                            DmaCopy16(3, dmaSrc, dmaDest, (s32)sp20);
                            dmaDest += sp0C;
                            dmaSrc += sp00 * bytesPerTileIndex;
                        }
                    }
                }
            }
        } else {
            if (!(bg->flags & BACKGROUND_FLAG_IS_LEVEL_MAP)) {
                while (bg->scrollX >= sp00 * 8)
                    bg->scrollX -= sp00 * 8;
                while (bg->scrollY >= bg->yTiles * 8) {
                    bg->scrollY -= bg->yTiles * 8;
                }
            }
            gBgScrollRegs[bgId][0] = bg->scrollX & 0x7;
            gBgScrollRegs[bgId][1] = bg->scrollY & 0x7;
            if ((bg->prevScrollX >> 3 != bg->scrollX >> 3) || (bg->prevScrollY >> 3 != bg->scrollY >> 3)) {
                if (!(bg->flags & BACKGROUND_FLAG_IS_LEVEL_MAP)) {
                    u16 *r7Ptr;
                    s16 r2;
                    u16 r5;
                    u16 *sp3C;
                    u32 notherIndex;
                    sp10 = (u16)((bg->scrollX >> 3) + bg->unk1E);
                    sp14 = (u16)((bg->scrollY >> 3) + bg->unk20);
                    notherIndex = (bg->unk24 * sp0C);
                    r7Ptr = CastPointer(bg->layoutVram, notherIndex);
                    r7Ptr = CastPointer(r7Ptr, bg->unk22 * bytesPerTileIndex);
                    if (((bg->targetTilesX + sp10) + 1) > bg->xTiles) {
                        r2 = (bg->targetTilesX + sp10) - (bg->xTiles - 1);
                    } else {
                        r2 = 0;
                    }
                    r5 = bg->targetTilesY + 1;
                    if (bg->flags & BACKGROUND_FLAG_100) {
                        if (bg->flags & BACKGROUND_FLAG_80) {
                            u32 index = ((bg->unk20 + r5) - 1) * bg->xTiles;
                            u16 *r1Ptr = CastPointer(bg->layout, index * bytesPerTileIndex);
                            u32 index2 = ((bg->unk1E + bg->targetTilesX) - 1);
                            u16 *r4Ptr = CastPointer(r1Ptr, index2 * bytesPerTileIndex);
                            while (r5-- != 0) {
                                for (k = 0; k < bg->targetTilesX; k++) {
                                    u32 mask = TileMask_FlipXY;
                                    sp3C = &r7Ptr[k];
                                    *sp3C = (r4Ptr[0 - k] ^ mask);
                                }
                                /* ROM 0x0810E3FE..0x0810E402 advances both rows. */
                                r7Ptr = CastPointer(r7Ptr, sp0C);
                                r4Ptr = CastPointer(r4Ptr, -(sp00 * bytesPerTileIndex));
                            }
                        } else {
                            u32 index;
                            u16 *r1Ptr;
                            u32 index2;
                            u16 *r4Ptr;
                            /* ROM 0x0810E414..0x0810E41A includes the source pitch. */
                            index = bg->unk20 * bg->xTiles;
                            index *= bytesPerTileIndex;
                            r1Ptr = (u16 *)&((u8 *)bg->layout)[index];
                            index2 = bg->unk1E + bg->targetTilesX - 1;
                            r4Ptr = CastPointer(r1Ptr, index2 * bytesPerTileIndex);
                            while (r5-- != 0) {
                                for (k = 0; k < bg->targetTilesX; k++) {
                                    sp3C = &r7Ptr[k];
                                    *sp3C = (r4Ptr[0 - k] ^ TileMask_FlipX);
                                }
                                r7Ptr = CastPointer(r7Ptr, sp0C);
                                r4Ptr = CastPointer(r4Ptr, sp00 * bytesPerTileIndex);
                            }
                        }
                    } else {
                        if (bg->flags & BACKGROUND_FLAG_80) {
                            u32 index = ((sp14 + r5) - 1) * bg->xTiles;
                            u16 *r0Ptr = (u16 *)&((u8 *)bg->layout)[index * bytesPerTileIndex];
                            u32 index2 = sp10;
                            /* Apply a byte offset, rather than scaling a u16 index twice. */
                            u16 *r4Ptr = CastPointer(r0Ptr,index2 * bytesPerTileIndex);
                            while (r5-- != 0) {
                                u16 k;
                                for (k = 0; k < bg->targetTilesX; k++) {
                                    sp3C = &r7Ptr[k];
                                    *sp3C = r4Ptr[k] ^ TileMask_FlipY;
                                }
                                r7Ptr = CastPointer(r7Ptr, sp0C);
                                r4Ptr = (void *)(((u8 *)r4Ptr) - sp00 * bytesPerTileIndex);
                            }
                        } else {
                            u32 index = (sp14 * bg->xTiles);
                            u16 *r0Ptr = CastPointer(bg->layout, index * bytesPerTileIndex);
                            u32 index2 = sp10;
                            u16 *r4Ptr = CastPointer(r0Ptr, index2 * bytesPerTileIndex);
                            while (r5-- != 0) {
                                s32 var = r2 - 1;
                                DmaCopy16(3, r4Ptr, r7Ptr, (s32)({
                                              dmaSize = bg->targetTilesX - var;
                                              dmaSize *= bytesPerTileIndex;
                                              dmaSize;
                                          }));
                                r7Ptr = CastPointer(r7Ptr, sp0C);
                                r4Ptr = CastPointer(r4Ptr, sp00 * bytesPerTileIndex);
                            }
                        }
                    }
                    if (r2 != 0) {
                        u8 *r1 = CastPointer(bg->layoutVram, bg->unk24 * sp0C); 
                        u32 displayTile = bg->unk22 + bg->xTiles - sp10; 
                        u16 *r7Ptr = CastPointer(r1, displayTile * bytesPerTileIndex);
                        u16 r5 = (bg->targetTilesY + 1);
                        if (bg->flags & BACKGROUND_FLAG_100) {
                            if (bg->flags & BACKGROUND_FLAG_80) {
                                u32 index = ((sp14 + r5) - 1) * bg->xTiles;
                                u16 *r1Ptr = CastPointer(bg->layout, index * bytesPerTileIndex);
                                u16 *r4Ptr = CastPointer(r1Ptr, (r2 - 1) * bytesPerTileIndex);
                                while (--r5 != (u16)-1) {
                                    for (k = 0; k < bg->targetTilesX; k++) {
                                        r7Ptr[k] = *(r4Ptr - k) ^ TileMask_FlipXY;
                                    }
                                    r7Ptr = CastPointer(r7Ptr, sp0C);
                                    r4Ptr = (u16 *)(((u8 *)r4Ptr) - sp00 * bytesPerTileIndex);
                                }
                            } else {
                                u32 index;
                                u16 *r4Ptr;
                                index = sp14 * bg->xTiles;
                                index *= bytesPerTileIndex;
                                r1 = &((u8 *)bg->layout)[index];
                                r4Ptr = (u16 *)&r1[(r2 - 1) * bytesPerTileIndex];
                                while (--r5 != (u16)-1) {
                                    for (k = 0; k < bg->targetTilesX; k++) {
                                        r7Ptr[k] = *(r4Ptr - k) ^ TileMask_FlipX;
                                    }
                                    r7Ptr = CastPointer(r7Ptr, sp0C);
                                    r4Ptr = CastPointer(r4Ptr, sp00 * bytesPerTileIndex);
                                }
                            }
                        } else {
                            if (bg->flags & BACKGROUND_FLAG_80) {
                                u32 index = ((sp14 + r5) - 1) * bg->xTiles;
                                u16 *r4Ptr = (u16 *)&((u8 *)bg->layout)[index * bytesPerTileIndex];
                                while (--r5 != (u16)-1) {
                                    for (k = 0; k < r2; k++) {
                                        u16 *sp3C = &r7Ptr[k];
                                        *sp3C = r4Ptr[k] ^ TileMask_FlipY;
                                    }
                                    r7Ptr = CastPointer(r7Ptr, sp0C);
                                    r4Ptr = (u16 *)(((u8 *)r4Ptr) - sp00 * bytesPerTileIndex);
                                }
                            } else {
                                u32 index = (sp14 * bg->xTiles);
                                u16 *r4Ptr = CastPointer(bg->layout, index * bytesPerTileIndex);
                                while (r5-- != 0) {
                                    dmaSize = bytesPerTileIndex * r2;
                                    DmaCopy16(3, r4Ptr, r7Ptr, (s32)dmaSize);
                                    r7Ptr = CastPointer(r7Ptr, sp0C);
                                    r4Ptr = CastPointer(r4Ptr, sp00 * bytesPerTileIndex);
                                }
                            }
                        }
                    }
                } else {
                    sp10 = (bg->scrollX / 8) + bg->unk1E;
                    sp14 = (bg->scrollY / 8) + bg->unk20;
                    for (i = 0; i < bg->targetTilesX;) {
                        s32 r4 = sp10 + i;
                        s32 sp24 = Div(r4, bg->xTiles);
                        s32 r1 = bg->xTiles;
                        s32 sp28 = r4 - (sp24 * r1);
                        s32 sp2C;
                        s32 r8 = bg->targetTilesY;
                        s32 remainingX = bg->targetTilesX - i;
                        r1 = r1 - sp28;
                        if (r1 > remainingX)
                            r1 = remainingX;
                        sp2C = r1 * bytesPerTileIndex;
                        for (j = 0; j < bg->targetTilesY;) {
                            s32 divident = sp14 + j;
                            s32 yPos = Div(divident, bg->yTiles);
                            s32 new_r4 = divident - (yPos * bg->yTiles);
                            s32 r5 = bg->yTiles - new_r4;
                            yPos *= bg->mapWidth;
                            { 
                                s32 metatileIndex;
                                s32 otherVal;
                                s32 mtIndex = *(&bg->metatileMap[yPos] + sp24);
#if NON_MATCHING
                                if (mtIndex >= 1024) {
                                    mtIndex = 0;
                                }
#endif
                                metatileIndex = mtIndex * bg->xTiles * bg->yTiles;
                                otherVal = new_r4 * bg->xTiles;
                                otherVal += sp28;
                                otherVal += metatileIndex;
                                {
                                    u8 *dmaSrc;
                                    u8 *dmaDest;
                                    u8 *destPtr;
                                    dmaSrc = CastPointer(bg->layout, otherVal * bytesPerTileIndex);
                                    destPtr = CastPointer(bg->layoutVram, bg->unk24);
                                    destPtr += sp0C * j;
                                    destPtr += +bg->unk22;
                                    dmaDest = CastPointer(destPtr, i * bytesPerTileIndex);
                                    j += r5;
                                    if (r5 > r8)
                                        r5 = r8;
                                    r8 -= r5;
                                    while (r5-- != 0) {
                                        dmaSize = sp2C;
                                        DmaCopy16(3, dmaSrc, dmaDest, (s32)dmaSize);
                                        dmaDest += sp0C;
                                        dmaSrc += sp00 * bytesPerTileIndex;
                                    }
                                }
                            }
                        }
                        i += r1;
                    }
                }
            }
        }
        REG_VCOUNT;
        bg->prevScrollX = bg->scrollX;
        bg->prevScrollY = bg->scrollY;
    }
    return 1;
}
