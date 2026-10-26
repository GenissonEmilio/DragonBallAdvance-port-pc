/* Algorithmic reading aid only; not a matching production source.
 * Signed GBA arithmetic and packed tile indices still require explicit wrap
 * semantics when this algorithm is adapted to a native host. */
#include "post_boot.h"
#include "sprites.h"
void Graphics_DrawSprite(struct DbaaPostBootSprite *sprite) {
  const struct DbaaFrameDimensions *dimensions;
  const struct DbaaOamAttributes *source;
  DbaaU32 flags, frame;
  int x, y;
  int width, height;
  DbaaU16 attr0 = 0, attr1 = 0, attr2 = 0;
  int flipY = 0, flipX = 0;
  DbaaU8 i;
  frame = sprite->frameIndex;
  if (frame == (DbaaU32)-1)
    return;
  if ((frame >> 28) == 0)
    dimensions = (const void *)gSpriteTables->dimensions[sprite->animation] + frame * 12;
  else
    dimensions = (const void *)gSpriteTables->dimensions[sprite->animation] + frame * 16;
  sprite->subframes = dimensions->subframes;
  x = sprite->x;
  y = sprite->y;
  flags = sprite->flags;
  if (flags & 0x20000) {
    x -= gSpriteOffset.x;
    y -= gSpriteOffset.y;
  }
  width = dimensions->width;
  height = dimensions->height;
  if (flags & 0x200)
    attr0 |= 0x1000;
  if (flags & 0x20) {
    attr0 |= 0x100;
    attr1 |= (flags & 0x1F) << 9;
    if (flags & 0x40) {
      x -= (DbaaU16)width / 2;
      y -= (DbaaU16)height / 2;
      width *= 2;
      height *= 2;
      attr0 |= 0x200;
    }
  } else {
    if (flags & 0x800)
      y -= height - dimensions->offsetY;
    else
      y -= dimensions->offsetY;
    if (flags & 0x400)
      x -= width - dimensions->offsetX;
    else
      x -= dimensions->offsetX;
    if (((flags >> 11) & 1) != (dimensions->oamIndexAndFlip >> 15))
      flipY = 1;
    if (((dimensions->oamIndexAndFlip >> 14) ^ (flags >> 10)) & 1)
      flipX = 1;
  }
  if (width != 0) {
    if (x + width < 0 || x > 240 || y + height < 0 || y > 160)
      return;
  }
  attr2 += sprite->palette << 12;
  attr0 |= (flags & 0x180) << 3;
  attr2 |= (flags & 0x3000) >> 2;
  source = gSpriteTables->oam[sprite->animation];
  sprite->oamStart = gOamFreeIndex;
  for (i = 0; i < dimensions->subframes; i++) {
    struct DbaaOamEntry *oam = Graphics_AllocateOam((sprite->order & 0x7C0) >> 6);
    int localX, localY;
    if (oam == gTaskHeapLimit)
      return;
    DMA_START((const void *)source + ((dimensions->oamIndexAndFlip & 0x3FFF) + i) * 6, oam, 0x80000003);
    localX = oam->attr1 & 0x1FF;
    localY = oam->attr0 & 0xFF;
    oam->attr1 &= 0xFE00;
    oam->attr0 &= 0xFE00;
    if (flipY | flipX) {
      DbaaU32 shape = ((oam->attr0 & 0xC000) >> 12) | ((oam->attr1 & 0xC000) >> 14);
      if (flipY) {
        oam->attr1 ^= 0x2000;
        localY = (height - gOamShapeSizes[shape][1]) - localY;
      }
      if (flipX) {
        oam->attr1 ^= 0x1000;
        localX = (width - gOamShapeSizes[shape][0]) - localX;
      }
    }
    {
      DbaaU32 a0 = ((y + localY) & 0xFF) + oam->attr0;
      DbaaU32 a1 = ((x + localX) & 0x1FF) + oam->attr1;
      oam->attr0 = a0 | attr0;
      oam->attr1 = a1 | attr1;
      oam->attr2 |= attr2;
      if (oam->attr0 & 0x2000)
        oam->attr2 += oam->attr2 & 0x3FF;
      oam->attr2 += ((DbaaU32)sprite->vram - 0x06010000) >> 5;
    }
  }
  if ((sprite->frameIndex >> 28) == 1 && (sprite->flags & 0x04000000)) {
    DbaaU32 tileInfo;
    const int *indices;
    const DbaaU8 *tiles, *begin;
    DbaaU8 *destination;
    int unit;
    DbaaU32 size;
    DbaaU8 count;
    sprite->flags &= ~0x04000000;
    tileInfo = *(const DbaaU32 *)((const void *)dimensions + 12);
    count = tileInfo >> 24;
    indices = gSpriteTables->tileIndices + (tileInfo & 0xFFFFFF);
    if (*indices >= 0) {
      unit = 32;
      tiles = gSpriteTables->tiles4;
    } else {
      unit = 64;
      tiles = gSpriteTables->tiles8;
    }
    size = unit;
    begin = tiles + *indices++ * size;
    destination = sprite->vram;
    for (i = 1; i < count; i++) {
      const DbaaU8 *next = tiles + *indices++ * unit;
      if (begin + size == next)
        size = (DbaaU16)(size + unit);
      else {
        gVramTransferQueue[gVramQueueWriteIndex].source = begin;
        gVramTransferQueue[gVramQueueWriteIndex].destination = destination;
        gVramTransferQueue[gVramQueueWriteIndex].size = size;
        gVramQueueWriteIndex = (gVramQueueWriteIndex + 1) & 0x7F;
        destination += size;
        size = unit;
        begin = next;
      }
    }
    gVramTransferQueue[gVramQueueWriteIndex].source = begin;
    gVramTransferQueue[gVramQueueWriteIndex].destination = destination;
    gVramTransferQueue[gVramQueueWriteIndex].size = size;
    gVramQueueWriteIndex = (gVramQueueWriteIndex + 1) & 0x7F;
  }
}
