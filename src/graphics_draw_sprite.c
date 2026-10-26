/* USA 0x08110CA0: 1188 complete bytes match the ROM. */
#include "sprites.h"
/* Empty constraints retain the recovered register/data flow. No template emits
 * instructions. Scratch slots retain the original word stores and truncations.
 */
#define IN_REGISTER(reg, expression)                                           \
  ({                                                                           \
    register DbaaU32 dbaaRegisterValue __asm__(reg) = (DbaaU32)(expression);   \
    __asm__("" : "+r"(dbaaRegisterValue));                                     \
    dbaaRegisterValue;                                                         \
  })
void Graphics_DrawSprite(struct DbaaPostBootSprite *input) {
  register struct DbaaPostBootSprite *sprite __asm__("r9") = input;
  register const struct DbaaFrameDimensions *dimensions __asm__("r8");

  register DbaaU32 flags __asm__("r5");
  DbaaU32 frame;
  register const struct DbaaSpriteTables *const *tableAddress __asm__("r3");
  register DbaaU32 animation __asm__("r2");

  register int y __asm__("r10");

  enum {
    DRAW_X,
    DRAW_WIDTH,
    DRAW_HEIGHT,
    DRAW_INDEX,
    DRAW_SOURCE,
    DRAW_ATTR0,
    DRAW_ATTR1,
    DRAW_ATTR2,
    DRAW_FLIP_Y,
    DRAW_FLIP_X,
    DRAW_TILE_COUNT,
    DRAW_SCRATCH_WORDS
  };
  volatile int scratch[DRAW_SCRATCH_WORDS];
  DbaaU8 i;
  __asm__("" : "+r"(sprite));
  scratch[DRAW_ATTR0] = ({
    register int value __asm__("r0") = 0;
    __asm__("" : "+r"(value));
    value;
  });
  scratch[DRAW_ATTR1] = ({
    register int value __asm__("r1") = 0;
    __asm__("" : "+r"(value));
    value;
  });
  scratch[DRAW_ATTR2] = ({
    register int value __asm__("r2") = 0;
    __asm__("" : "+r"(value));
    value;
  });
  scratch[DRAW_FLIP_Y] = ({
    register int value __asm__("r3") = 0;
    __asm__("" : "+r"(value));
    value;
  });
  scratch[DRAW_FLIP_X] = ({
    register int value __asm__("r4") = 0;
    __asm__("" : "+r"(value));
    value;
  });
  frame = sprite->frameIndex;
  if (frame == (DbaaU32)-1)
    return;
  /* Compact and extended frame records have strides 12 and 16. */
  if ((frame >> 28) == 0) {
    tableAddress = &gSpriteTables;
    __asm__("" : "+r"(tableAddress));
    dimensions =
        (const void *)((const struct DbaaSpriteTables *)IN_REGISTER(
                           "r0", *tableAddress))
            ->dimensions[(animation = ((struct DbaaPostBootSprite *)IN_REGISTER(
                                           "r1", sprite))
                                          ->animation)] +
        frame * 12;
  } else {
    tableAddress = &gSpriteTables;
    __asm__("" : "+r"(tableAddress));
    dimensions =
        (const void *)((const struct DbaaSpriteTables *)IN_REGISTER(
                           "r0", *tableAddress))
            ->dimensions[(animation = ((struct DbaaPostBootSprite *)IN_REGISTER(
                                           "r1", sprite))
                                          ->animation)] +
        frame * 16;
  }
  {
    register const struct DbaaFrameDimensions *base __asm__("r4") = dimensions;
    register DbaaU32 count __asm__("r0");
    register struct DbaaPostBootSprite *record __asm__("r1");
    __asm__("" : "+r"(base));
    count = base->subframes;
    __asm__("" : "+r"(count));
    record = sprite;
    __asm__("" : "+r"(record) : "r"(count));
    record->subframes = count;
    scratch[DRAW_X] = (int)IN_REGISTER("r4", record->x);
    y = (int)IN_REGISTER("r1", record->y);
  }
  {
    register DbaaU32 loaded __asm__("r1") =
        ((struct DbaaPostBootSprite *)IN_REGISTER("r0", sprite))->flags;
    register DbaaU32 relative __asm__("r0") = loaded & 0x20000;
    __asm__("" : "+r"(relative) : "r"(loaded));
    flags = loaded;
    __asm__("" : "+r"(flags) : "r"(relative));
    if (relative) {
      register const struct DbaaSpriteOffset *offset __asm__("r0") =
          &gSpriteOffset;
      int deltaX;
      __asm__("" : "+r"(offset));
      deltaX = offset->x;
      scratch[DRAW_X] = (int)IN_REGISTER("r4", scratch[DRAW_X]) - deltaX;
      y -= offset->y;
    }
  }
  scratch[DRAW_WIDTH] =
      ((const struct DbaaFrameDimensions *)IN_REGISTER("r0", dimensions))
          ->width;
  scratch[DRAW_HEIGHT] = IN_REGISTER(
      "r1", ((const struct DbaaFrameDimensions *)IN_REGISTER("r1", dimensions))
                ->height);
  {
    register DbaaU32 doubleMask __asm__("r1") = 0x200;
    __asm__("" : "+r"(doubleMask));
    if (flags & doubleMask) {
      register DbaaU32 addend __asm__("r0") = IN_REGISTER("r4", 0x1000);
      register DbaaU32 value __asm__("r4");
      __asm__("" : "+r"(addend));
      value = scratch[DRAW_ATTR0];
      value |= addend;
      __asm__("" : "+r"(value));
      scratch[DRAW_ATTR0] = value;
    }
    if (flags & 0x20) {
      {
        register DbaaU32 addend __asm__("r0") = IN_REGISTER("r4", 0x100);
        register DbaaU32 value __asm__("r4");
        __asm__("" : "+r"(addend));
        value = scratch[DRAW_ATTR0];
        value |= addend;
        __asm__("" : "+r"(value));
        scratch[DRAW_ATTR0] = IN_REGISTER("r0", (DbaaU16)value);
      }
      {
        register DbaaU32 addend __asm__("r0") =
            (flags & IN_REGISTER("r0", 0x1F)) << 9;
        register DbaaU32 value __asm__("r4");
        __asm__("" : "+r"(addend));
        value = scratch[DRAW_ATTR1];
        value |= addend;
        __asm__("" : "+r"(value));
        scratch[DRAW_ATTR1] = value;
      }
      if (flags & 0x40) {
        {
          register int half __asm__("r0") =
              (DbaaU16)IN_REGISTER("r4", scratch[DRAW_WIDTH]) / 2;
          __asm__("" : "+r"(half));
          {
            register int position __asm__("r4") = scratch[DRAW_X];
            __asm__("" : "+r"(position));
            position -= half;
            __asm__("" : "+r"(position));
            scratch[DRAW_X] = position;
          }
          half = (DbaaU16)IN_REGISTER("r4", scratch[DRAW_HEIGHT]) / 2;
          __asm__("" : "+r"(half));
          {
            register int position __asm__("r4") = y;
            __asm__("" : "+r"(position));
            position -= half;
            __asm__("" : "+r"(position));
            y = position;
          }
        }
        scratch[DRAW_WIDTH] *= 2;
        {
          register DbaaU32 doubled __asm__("r4") = scratch[DRAW_HEIGHT];
          __asm__("" : "+r"(doubled));
          doubled <<= 1;
          __asm__("" : "+r"(doubled));
          scratch[DRAW_HEIGHT] = doubled;
        }
        scratch[DRAW_ATTR0] |= doubleMask;
      }
    } else {
      if (flags & 0x800) {
        register int offset __asm__("r0") = (int)IN_REGISTER(
            "r0",
            ((const struct DbaaFrameDimensions *)IN_REGISTER("r1", dimensions))
                ->offsetY);
        register int position __asm__("r4");
        offset = (int)IN_REGISTER("r1", scratch[DRAW_HEIGHT]) - offset;
        __asm__("" : "+r"(offset));
        position = y;
        __asm__("" : "+r"(position));
        position -= offset;
        __asm__("" : "+r"(position));
        y = position;
      } else {
        y -= (int)IN_REGISTER(
            "r0",
            ((const struct DbaaFrameDimensions *)IN_REGISTER("r1", dimensions))
                ->offsetY);
      }
      if (flags & 0x400) {
        register int offset __asm__("r0") = (int)IN_REGISTER(
            "r0",
            ((const struct DbaaFrameDimensions *)IN_REGISTER("r4", dimensions))
                ->offsetX);
        register int position __asm__("r1");
        offset = (int)IN_REGISTER("r4", scratch[DRAW_WIDTH]) - offset;
        __asm__("" : "+r"(offset));
        position = scratch[DRAW_X];
        position -= offset;
        __asm__("" : "+r"(position));
        scratch[DRAW_X] = position;
      } else {
        register int offset __asm__("r0") = (int)IN_REGISTER(
            "r0",
            ((const struct DbaaFrameDimensions *)IN_REGISTER("r4", dimensions))
                ->offsetX);
        register int position __asm__("r4") = scratch[DRAW_X];
        position -= offset;
        __asm__("" : "+r"(position));
        scratch[DRAW_X] = position;
      }
      {
        register DbaaU32 vertical __asm__("r0") = flags >> 11;
        register DbaaU32 mask __asm__("r6") = 1;
        register DbaaU32 packed __asm__("r4");
        __asm__("" : "+r"(mask) : "r"(vertical));
        vertical &= mask;
        __asm__("" : "+r"(vertical));
        packed =
            IN_REGISTER("r1", ((const struct DbaaFrameDimensions *)IN_REGISTER(
                                   "r4", dimensions))
                                  ->oamIndexAndFlip)
            << 16;
        __asm__("" : "+r"(packed));
        if (vertical != (packed >> 31))
          scratch[DRAW_FLIP_Y] = IN_REGISTER("r0", 1);
        {
          register DbaaU32 horizontal __asm__("r1") = flags >> 10;
          register DbaaU32 frameHorizontal __asm__("r0");
          __asm__("" : "+r"(horizontal));
          frameHorizontal = packed >> 30;
          __asm__("" : "+r"(frameHorizontal) : "r"(horizontal));
          if ((frameHorizontal ^ horizontal) & mask)
            scratch[DRAW_FLIP_X] = IN_REGISTER("r1", 1);
        }
      }
    }
  }
  {
    register int screenWidth __asm__("r4") = scratch[DRAW_WIDTH];
    __asm__("" : "+r"(screenWidth));
    if (screenWidth != 0) {
      {
        register int screenX __asm__("r1") = scratch[DRAW_X];
        register int sum __asm__("r0");
        __asm__("" : "+r"(screenX));
        sum = screenX + screenWidth;
        __asm__("" : "+r"(sum));
        if (sum < 0 || screenX > 240 || y + scratch[DRAW_HEIGHT] < 0 || y > 160)
          return;
      }
    }
  }
  {
    register DbaaU32 palette __asm__("r1") = IN_REGISTER("r1", sprite->palette)
                                             << 12;
    register DbaaU32 addend __asm__("r0");
    palette = IN_REGISTER("r4", scratch[DRAW_ATTR2]) + palette;
    palette <<= 16;
    __asm__("" : "+r"(palette));
    addend = (flags & 0x180) << 3;
    __asm__("" : "+r"(addend));
    {
      register DbaaU32 value __asm__("r4") = scratch[DRAW_ATTR0];
      value |= addend;
      __asm__("" : "+r"(value));
      scratch[DRAW_ATTR0] = value;
    }
    addend = (flags & 0x3000) << 14;
    addend |= palette;
    __asm__("" : "+r"(addend));
    scratch[DRAW_ATTR2] = addend >> 16;
  }
  __asm__("" : "+r"(tableAddress), "+r"(animation));
  {
    register const struct DbaaOamAttributes *const *oamTable __asm__("r1") =
        (*tableAddress)->oam;
    __asm__("" : "+r"(oamTable));
    scratch[DRAW_SOURCE] = *(const int *)IN_REGISTER(
        "r0", IN_REGISTER("r0", animation << 2) + (DbaaU32)oamTable);
  }
  {
    register DbaaU32 firstOam __asm__("r0") = gOamFreeIndex;
    __asm__("" : "+r"(firstOam));
    ((struct DbaaPostBootSprite *)IN_REGISTER("r1", sprite))->oamStart =
        firstOam;
  }
  {
    DbaaU32 initial = IN_REGISTER("r2", 0);
    scratch[DRAW_INDEX] = initial;
    if (initial < IN_REGISTER("r3", ((const struct DbaaFrameDimensions *)
                                         IN_REGISTER("r3", dimensions))
                                        ->subframes)) {
      do {
        struct DbaaOamEntry *oam = Graphics_AllocateOam(
            (((struct DbaaPostBootSprite *)IN_REGISTER("r4", sprite))->order &
             0x7C0) >>
            6);
        register int localX __asm__("r7");
        register int localY __asm__("r5");
        register DbaaU32 oldA1 __asm__("r1");
        register DbaaU32 oldA0 __asm__("r2");
        register DbaaU32 maskedA1 __asm__("r3");
        register DbaaU32 maskedA0 __asm__("r1");
        if (gTaskHeapLimit == oam)
          return;
        {
          register const struct DbaaFrameDimensions *base __asm__("r3") =
              dimensions;
          register DbaaU32 frameOam __asm__("r0");
          register DbaaU32 offset __asm__("r1");
          __asm__("" : "+r"(base));
          frameOam = base->oamIndexAndFlip;
          __asm__("" : "+r"(frameOam));
          offset = IN_REGISTER("r2", 0x3FFF) & frameOam;
          offset += IN_REGISTER("r3", scratch[DRAW_INDEX]);
          __asm__("" : "+r"(offset));
          {
            register DbaaU32 sourceOffset __asm__("r0") = offset * 6;
            register volatile DbaaU32 *dma __asm__("r2");
            __asm__("" : "+r"(sourceOffset));
            sourceOffset =
                IN_REGISTER("r1", scratch[DRAW_SOURCE]) + sourceOffset;
            __asm__("" : "+r"(sourceOffset));
            dma = (volatile DbaaU32 *)0x040000D4;
            __asm__("" : "+r"(dma));
            dma[0] = sourceOffset;
            dma[1] = (DbaaU32)oam;
            dma[2] = 0x80000003;
            (void)dma[2];
          }
        }
        oldA1 = oam->attr1;
        __asm__("" : "+r"(oldA1));
        localX = IN_REGISTER("r0", IN_REGISTER("r3", 0x1FF)) & oldA1;
        __asm__("" : "+r"(localX));
        oldA0 = oam->attr0;
        localY = *(DbaaU8 *)oam;
        __asm__("" : "+r"(oldA0), "+r"(localY));
        {
          register DbaaU32 mask __asm__("r0") = 0xFE00;
          __asm__("" : "+r"(mask));
          maskedA1 = mask & oldA1;
          __asm__("" : "+r"(maskedA1));
          oam->attr1 = maskedA1;
          maskedA0 = mask & oldA0;
          __asm__("" : "+r"(maskedA0));
          oam->attr0 = maskedA0;
        }
        if (IN_REGISTER("r0", scratch[DRAW_FLIP_Y]) |
            IN_REGISTER("r2", scratch[DRAW_FLIP_X])) {
          register DbaaU32 vertical __asm__("r0") = maskedA0;
          register DbaaU32 mask __asm__("r1");
          register DbaaU32 shape __asm__("r2");
          register DbaaU32 savedShape __asm__("r6");
          __asm__("" : "+r"(vertical));
          mask = 0xC000;
          __asm__("" : "+r"(mask));
          vertical &= mask;
          shape = vertical >> 12;
          __asm__("" : "+r"(shape));
          vertical = maskedA1;
          __asm__("" : "+r"(vertical));
          vertical &= mask;
          vertical >>= 14;
          shape |= vertical;
          __asm__("" : "+r"(shape));
          savedShape = shape;
          __asm__("" : "+r"(savedShape) : "r"(shape));
          if (scratch[DRAW_FLIP_Y]) {
            register int size __asm__("r0");
            oam->attr1 = IN_REGISTER(
                "r0", maskedA1 ^ IN_REGISTER("r1", IN_REGISTER("r0", 0x2000)));
            size = IN_REGISTER("r0", shape << 1);
            size = *(
                const DbaaU8 *)(size +
                                IN_REGISTER(
                                    "r1", (const DbaaU8 *)gOamShapeSizes + 1));
            __asm__("" : "+r"(size));
            size = (int)IN_REGISTER("r2", scratch[DRAW_HEIGHT]) - size;
            __asm__("" : "+r"(size));
            localY = size - localY;
            __asm__("" : "+r"(localY));
          }
          if (IN_REGISTER("r3", scratch[DRAW_FLIP_X])) {
            register int size __asm__("r0");
            {
              register DbaaU32 a1 __asm__("r0") = oam->attr1;
              __asm__("" : "+r"(a1));
              a1 ^= IN_REGISTER("r1", IN_REGISTER("r2", 0x1000));
              __asm__("" : "+r"(a1));
              oam->attr1 = a1;
            }
            size = IN_REGISTER("r0", savedShape << 1);
            size = *(const DbaaU8 *)(size + IN_REGISTER("r3", gOamShapeSizes));
            __asm__("" : "+r"(size));
            size = (int)IN_REGISTER("r1", scratch[DRAW_WIDTH]) - size;
            __asm__("" : "+r"(size));
            localX = size - localX;
            __asm__("" : "+r"(localX));
          }
        }
        {
          register DbaaU32 a0 __asm__("r2") =
              ((int)IN_REGISTER("r3", y) + localY) & 0xFF;
          register DbaaU32 a1 __asm__("r0");
          register DbaaU32 a2 __asm__("r3");
          __asm__("" : "+r"(a0));
          a0 += IN_REGISTER("r0", oam->attr0);
          __asm__("" : "+r"(a0));
          a1 = (int)IN_REGISTER("r1", scratch[DRAW_X]) + localX;
          __asm__("" : "+r"(a1));
          a1 &= IN_REGISTER("r1", IN_REGISTER("r3", 0x1FF));
          a1 += IN_REGISTER("r1", oam->attr1);
          __asm__("" : "+r"(a1));
          a0 |= IN_REGISTER("r3", scratch[DRAW_ATTR0]);
          __asm__("" : "+r"(a0));
          oam->attr0 = a0;
          a1 |= IN_REGISTER("r1", scratch[DRAW_ATTR1]);
          __asm__("" : "+r"(a1));
          oam->attr1 = a1;
          a2 = IN_REGISTER("r0", oam->attr2) |
               IN_REGISTER("r3", scratch[DRAW_ATTR2]);
          __asm__("" : "+r"(a2));
          oam->attr2 = a2;
          if (a0 & IN_REGISTER("r0", IN_REGISTER("r1", 0x2000)))
            oam->attr2 = IN_REGISTER(
                "r0", a2 + (a2 & IN_REGISTER("r1", IN_REGISTER("r2", 0x3FF))));
          oam->attr2 +=
              ((DbaaU32)((struct DbaaPostBootSprite *)IN_REGISTER("r3", sprite))
                   ->vram -
               0x06010000) >>
              5;
        }
        {
          DbaaU32 next = (DbaaU8)(scratch[DRAW_INDEX] + 1);
          scratch[DRAW_INDEX] = next;
          if (next >= IN_REGISTER("r3", ((const struct DbaaFrameDimensions *)
                                             IN_REGISTER("r3", dimensions))
                                            ->subframes))
            break;
        }
      } while (1);
    }
  }
  {
    /* Extended frames can enqueue runs of contiguous tile data. */
    register struct DbaaPostBootSprite *record __asm__("r4") = sprite;
    __asm__("" : "+r"(record));
    if ((record->frameIndex >> 28) == 1) {
      register DbaaU32 state __asm__("r1") = record->flags;
      __asm__("" : "+r"(state));
      if (state & IN_REGISTER("r0", 0x04000000)) {
        register DbaaU32 tileInfo __asm__("r0");
        register DbaaU32 id __asm__("r1");
        register const struct DbaaSpriteTables *tables __asm__("r2");
        const int *indices;
        register const DbaaU8 *tiles __asm__("r8");
        register const DbaaU8 *begin __asm__("r2");
        register DbaaU8 *destination __asm__("r6");
        register int unit __asm__("r12");
        register DbaaU32 size __asm__("r3");
        state &= IN_REGISTER("r0", ~0x04000000);
        record->flags = state;
        tileInfo =
            ((const struct DbaaExtendedFrame *)IN_REGISTER("r1", dimensions))
                ->tileInfo;
        __asm__("" : "+r"(tileInfo));
        id = IN_REGISTER("r1", 0xFFFFFF) & tileInfo;
        __asm__("" : "+r"(id));
        scratch[DRAW_TILE_COUNT] = IN_REGISTER("r0", tileInfo >> 24);
        tables = *(const struct DbaaSpriteTables **)IN_REGISTER("r0",
                                                                &gSpriteTables);
        __asm__("" : "+r"(tables));
        indices = tables->tileIndices + id;
        if (*indices >= 0) {
          unit = IN_REGISTER("r3", 32);
          tiles = (const DbaaU8 *)IN_REGISTER("r2", tables->tiles4);
        } else {
          unit = IN_REGISTER("r4", 64);
          tiles = (const DbaaU8 *)IN_REGISTER("r2", tables->tiles8);
        }
        size = IN_REGISTER("r3", unit);
        {
          /* Reserve the scratch register across the cursor load. */
          register DbaaU32 preserved __asm__("r4");
          register int offset __asm__("r0");
          __asm__ volatile("" : "=r"(preserved) : : "memory");
          offset = *indices++ * size;
          __asm__ volatile("" : : "r"(preserved), "r"(offset));
          __asm__("" : "+r"(offset));
          begin = (const DbaaU8 *)IN_REGISTER("r4", tiles) + offset;
          __asm__("" : "+r"(begin));
        }
        destination = sprite->vram;
        __asm__("" : "+r"(destination));
        i = 1;
        if (i < IN_REGISTER("r1", scratch[DRAW_TILE_COUNT])) {
          register struct DbaaVramTransfer *queue __asm__("r9") =
              (void *)IN_REGISTER("r4", gVramTransferQueue);
          __asm__("" : "+r"(queue));
          do {
            const DbaaU8 *next =
                tiles + ({
                          /* Reserve the scratch register across the cursor
                           * load. */
                          register DbaaU32 preserved __asm__("r4");
                          register int tile __asm__("r0");
                          __asm__ volatile("" : "=r"(preserved) : : "memory");
                          tile = *indices++;
                          __asm__ volatile("" : : "r"(preserved), "r"(tile));
                          tile;
                        }) * unit;
            if (begin + size == next) {
              register DbaaU32 combined __asm__("r0") =
                  size + IN_REGISTER("r4", unit);
              __asm__("" : "+r"(combined));
              size = (DbaaU16)combined;
            } else {
              queue[gVramQueueWriteIndex].source = (DbaaU32)begin;
              {
                register DbaaU32 offset __asm__("r0") =
                    gVramQueueWriteIndex * 12;
                __asm__("" : "+r"(offset));
                *(DbaaU32 *)IN_REGISTER(
                    "r0", offset + IN_REGISTER("r1", (DbaaU8 *)queue + 4)) =
                    (DbaaU32)destination;
              }
              queue[gVramQueueWriteIndex].size = size;
              gVramQueueWriteIndex = (gVramQueueWriteIndex + 1) & 0x7F;
              destination += size;
              size = IN_REGISTER("r3", unit);
              begin = next;
            }
            i++;
          } while (i < (DbaaU32)scratch[DRAW_TILE_COUNT]);
        }
        gVramTransferQueue[gVramQueueWriteIndex].source = (DbaaU32)begin;
        gVramTransferQueue[gVramQueueWriteIndex].destination =
            (DbaaU32)destination;
        gVramTransferQueue[gVramQueueWriteIndex].size = size;
        gVramQueueWriteIndex = (gVramQueueWriteIndex + 1) & 0x7F;
      }
    }
  }
}
