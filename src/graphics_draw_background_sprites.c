/* DBAA USA 0x0810EFB4..0x0810F4F0: complete byte match with agbcc -O2.
 * Empty GNU C asm statements constrain register allocation and value lifetimes;
 * every template is empty and emits no machine instructions. They are matching
 * aids, not evidence that the original source contained these statements.
 * OAM DMA records advance by six bytes; the local ABI scratch occupies eight.
 */
#include "backgrounds.h"
#undef DMA_START
#define DMA_START(s, d, c)                                                                         \
    {                                                                                              \
        register volatile DbaaU32 *dma __asm__("r1") = (volatile DbaaU32 *)0x040000D4;             \
        __asm__("" : : "r"(dma));                                                                  \
        dma[0] = (DbaaU32)(s);                                                                     \
        dma[1] = (DbaaU32)(d);                                                                     \
        dma[2] = (c);                                                                              \
        dma[2];                                                                                    \
    }

int Graphics_DrawBackgroundSprites(void)
{
    struct DbaaOamAttributes oamData;
    struct DbaaOamAttributes *oamPtr;
    DbaaU8 i, j;
    struct DbaaBgSprite *sprite;
    const struct DbaaFrameDimensions *dimensions;
    DbaaU32 pitch;
    void *charBase, *mapBase;
    const struct DbaaOamAttributes *source;
    DbaaU8 width, height;
    register int x __asm__("r8");
    int y;
    DbaaU16 tile, pair;
    int tileShift = 5;
    DbaaU8 xStep, yStep, columns;
    void *row;
    if (!(REG_DISPSTAT & 1))
        return 0;
    if (gBgSpriteCount != 0) {
        for (i = 0; i < gBgSpriteCount; i++) {
            sprite = gBgSpriteQueue[i];
            if (sprite->frameIndex != (DbaaU32)-1) {
                DbaaU32 bg;
                if ((sprite->frameIndex >> 28) == 0)
                    dimensions = (const void *)gSpriteTables->dimensions[sprite->animation] +
                                 sprite->frameIndex * 12;
                else
                    dimensions = (const void *)gSpriteTables->dimensions[sprite->animation] +
                                 sprite->frameIndex * 16;
                bg = (sprite->flags & 0x18000) >> 15;
                charBase = (void *)0x06000000 + ((gBgControlShadow[bg] & 12) << 12);
                mapBase = (void *)0x06000000 + ((gBgControlShadow[bg] & 0x1f00) << 3);
                if (gBgControlShadow[bg] & 0x80)
                    tileShift = 6;
                if (bg >= 2 && (gDisplayControlShadow & 3)) {
                    pitch = (DbaaU16)(16 << (gBgControlShadow[bg] >> 14));
                    source = gSpriteTables->oam[sprite->animation];
                    source = (const void *)source + (dimensions->oamIndexAndFlip & 0x3fff) * 6;
                    j = 0;
                    if (j < dimensions->subframes) {
                        oamPtr = &oamData;
                        __asm__(""
                                : "+r"(oamPtr)
                                :
                                : "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7");
                        do {
                            yStep = pitch;
                            DMA_START(source, &oamData, 0x80000003);
                            source = (const void *)source + 6;
                            width = gOamShapeSizes[((oamPtr->a0 & 0xc000) >> 12) |
                                                   ((oamPtr->a1 & 0xc000) >> 14)][0] >>
                                    3;
                            height = gOamShapeSizes[((oamPtr->a0 & 0xc000) >> 12) |
                                                    ((oamPtr->a1 & 0xc000) >> 14)][1] >>
                                     3;
                            y = sprite->y - dimensions->offsetY;
                            {
                                register int position __asm__("r1") = sprite->x;
                                __asm__("" : "+r"(position));
                                position -= dimensions->offsetX;
                                __asm__("" : "+r"(position));
                                x = position;
                            }
                            __asm__("" : "+r"(x));
                            x &= ~15;
                            row = mapBase + ((y + (oamPtr->a0 & 0xff)) >> 3) * pitch;
                            tile = (((sprite->destination - (DbaaU32)charBase) >> tileShift) +
                                    (oamPtr->a2 & 0x3ff)) &
                                   0xff;
                            while (height-- > 0) {
                                void *destination = row + (((oamPtr->a1 & 0x1ff) + x) >> 3);
                                columns = width;
                                while (columns-- > 0) {
                                    if (!((DbaaU32)destination & 1))
                                        pair = tile;
                                    else {
                                        pair |= tile << 8;
                                        *(DbaaU16 *)destination = pair;
                                    }
                                    tile++;
                                    destination++;
                                }
                                {
                                    register DbaaU32 tail __asm__("r0") = (DbaaU32)destination;
                                    __asm__("" : "+r"(tail));
                                    tail &= 1;
                                    if (tail) {
                                        register DbaaU32 old __asm__("r1") =
                                            *(DbaaU16 *)destination;
                                        *(DbaaU16 *)destination = (old & 0xff00) | pair;
                                        __asm__("" : : "r"(old));
                                    }
                                }
                                row += (DbaaS8)yStep;
                            }

                        } while (++j < dimensions->subframes);
                    }
                } else {
                    register DbaaU32 size __asm__("r1");
                    DbaaU32 difference;
                    register DbaaU32 control __asm__("r0");
                    pitch = 32;
                    control = gBgControlShadow[bg];
                    __asm__("" : : "r"(control));
                    size = control >> 14;
                    difference = size - 2;
                    __asm__("" : : "r"(size));
                    if ((DbaaU8)difference <= 1)
                        pitch = 64;
                    source = gSpriteTables->oam[sprite->animation];
                    source = (const void *)source + (dimensions->oamIndexAndFlip & 0x3fff) * 6;
                    j = 0;
                    if (j < dimensions->subframes) {
                        oamPtr = &oamData;
                        __asm__(""
                                : "+r"(oamPtr)
                                :
                                : "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7");
                        do {
                            DbaaU16 oamX, oamY;
                            register DbaaU32 yFlip __asm__("r1"), mask __asm__("r5");
                            DbaaU32 expected;
                            register DbaaU32 xFlip __asm__("r0"), xFlags __asm__("r1"),
                                xMask __asm__("r3");
                            DMA_START(source, &oamData, 0x80000003);
                            source = (const void *)source + 6;
                            width = gOamShapeSizes[((oamPtr->a0 & 0xc000) >> 12) |
                                                   ((oamPtr->a1 & 0xc000) >> 14)][0] >>
                                    3;
                            height = gOamShapeSizes[((oamPtr->a0 & 0xc000) >> 12) |
                                                    ((oamPtr->a1 & 0xc000) >> 14)][1] >>
                                     3;
                            oamX = oamPtr->a1 & 0x1ff;
                            oamY = oamPtr->a0 & 0xff;
                            oamPtr->a2 += sprite->palette << 12;
                            yFlip = sprite->flags >> 11;
                            mask = 1;
                            __asm__("" : : "r"(yFlip), "r"(mask));
                            yFlip &= mask;
                            expected = dimensions->oamIndexAndFlip >> 15;
                            __asm__("" : : "r"(mask));
                            if (yFlip != expected) {
                                oamPtr->a1 ^= 0x2000;
                                {
                                    register int position __asm__("r0"), offset __asm__("r1");
                                    if (dimensions->oamIndexAndFlip & 0x4000) {
                                        position = sprite->y;
                                        offset = dimensions->offsetY;
                                    } else {
                                        register const struct DbaaFrameDimensions *view __asm__(
                                            "r2");
                                        register int extent __asm__("r1"), pivot __asm__("r2");
                                        position = sprite->y;
                                        view = dimensions;
                                        __asm__("" : : "r"(view));
                                        extent = view->height;
                                        pivot = view->offsetY;
                                        __asm__("" : : "r"(extent), "r"(pivot));
                                        offset = extent - pivot;
                                    }
                                    __asm__("" : "+r"(offset));
                                    position += offset;
                                    __asm__("" : "+r"(position));
                                    y = position;
                                    y -= 8;
                                }
                                {
                                    DbaaU32 shifted = oamY << 16;
                                    __asm__("" : "+r"(shifted));
                                    oamY = (-shifted) >> 16;
                                }
                            } else
                                y = sprite->y - dimensions->offsetY;
                            xFlags = sprite->flags >> 10;
                            xFlip = dimensions->oamIndexAndFlip >> 14;
                            __asm__("" : "+r"(xFlip) : "r"(xFlags));
                            xFlip ^= xFlags;
                            xMask = 1;
                            __asm__("" : : "r"(xMask));
                            xFlip &= xMask;
                            if (xFlip) {
                                oamPtr->a1 ^= 0x1000;
                                __asm__("" : : "r"(xMask));
                                {
                                    register int position __asm__("r0"), offset __asm__("r1");
                                    register const struct DbaaFrameDimensions
                                        *flipDimensions __asm__("r3") = dimensions;
                                    __asm__("" : "+r"(flipDimensions));
                                    if (flipDimensions->oamIndexAndFlip & 0x4000) {
                                        position = sprite->x;
                                        offset = flipDimensions->offsetX;
                                    } else {
                                        position = sprite->x;
                                        offset = dimensions->width;
                                        __asm__("" : "+r"(offset));
                                        offset -= dimensions->offsetX;
                                    }
                                    __asm__("" : "+r"(offset));
                                    position += offset;
                                    position -= 8;
                                    __asm__("" : "+r"(position));
                                    x = position;
                                }
                                {
                                    DbaaU32 shifted = oamX << 16;
                                    __asm__("" : "+r"(shifted));
                                    oamX = (-shifted) >> 16;
                                }
                            } else {
                                register int position __asm__("r1") = sprite->x;
                                __asm__("" : "+r"(position));
                                position -= dimensions->offsetX;
                                __asm__("" : "+r"(position));
                                x = position;
                            }
                            __asm__("" : "+r"(x));
                            x &= ~15;
                            y &= ~7;
                            if (oamPtr->a1 & 0x1000)
                                xStep = -2;
                            else
                                xStep = 2;
                            {
                                register DbaaU32 shifted __asm__("r0");
                                if (oamPtr->a1 & 0x2000) {
                                    register DbaaU32 rowPitch __asm__("r7") = pitch;
                                    __asm__("" : "+r"(rowPitch));
                                    shifted = rowPitch << 25;
                                    __asm__("" : "+r"(shifted));
                                    shifted = -shifted;
                                } else {
                                    __asm__("" : : : "r7");
                                    shifted = pitch << 25;
                                }
                                yStep = shifted >> 24;
                            }
                            row = mapBase + ((y + (DbaaS16)oamY) >> 2) * pitch;
                            tile =
                                ((sprite->destination - (DbaaU32)charBase) >> tileShift) +
                                (oamPtr->a2 & 0xf3ff) +
                                ((((volatile struct DbaaOamAttributes *)oamPtr)->a1 & 0x3000) >> 2);
                            {
                                int horizontalOffset;
                                if (height-- > 0) {
                                    horizontalOffset = (x + (DbaaS16)oamX) >> 2;
                                    do {
                                        void *destination = row + horizontalOffset;
                                        columns = width;
                                        while (columns-- > 0) {
                                            *(DbaaU16 *)destination = tile++;
                                            destination += (DbaaS8)xStep;
                                        }
                                        row += (DbaaS8)yStep;
                                    } while (height-- > 0);
                                }
                            }

                        } while (++j < dimensions->subframes);
                    }
                }
            }
        }
        gBgSpriteCount = 0;
    }
    return 1;
}
