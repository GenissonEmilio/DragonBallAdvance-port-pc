#ifndef DBAA_BACKGROUNDS_H
#define DBAA_BACKGROUNDS_H
#include "graphics.h"
struct DbaaFrameDimensions {
    DbaaU16 oamIndexAndFlip,subframes,width,height;
    DbaaS16 offsetX,offsetY;
};
struct DbaaExtendedFrame {struct DbaaFrameDimensions base; DbaaU32 tileInfo;};
struct DbaaBgSprite {
    DbaaU32 destination,frameIndex,flags;
    DbaaU16 animation,unknown0E;
    DbaaS16 x,y;
    DbaaU8 unknown14[11],palette;
};
struct DbaaOamAttributes {DbaaU16 a0,a1,a2;};
struct DbaaSpriteTables {const int *const *const *animations; const void *const *dimensions; const struct DbaaOamAttributes *const *oam; const void *palettes; const DbaaU8 *tiles4, *tiles8; const int *tileIndices;};
extern const struct DbaaSpriteTables *gSpriteTables;
extern struct DbaaBgSprite *gBgSpriteQueue[];
extern DbaaU8 gBgSpriteCount;
extern const DbaaU8 gOamShapeSizes[12][2];

struct DbaaBackground {
    DbaaU8 unknown00[12];
    void *layoutVram;
    const DbaaU16 *layout;
    DbaaU16 xTiles,yTiles,unknown18[3],unk1E,unk20,unk22,unk24;
    DbaaU16 targetTilesX,targetTilesY,unknown2A,tilemapId,flags;
    DbaaU16 scrollX,scrollY,prevScrollX,prevScrollY;
    const DbaaU16 *metatileMap;
    DbaaU16 mapWidth,mapHeight;
};
extern struct DbaaBackground *gBackgroundQueue[16];
extern DbaaU8 gBackgroundReadIndex,gBackgroundWriteIndex;
extern DbaaU16 gBackgroundScroll[4][2];
int Bios_Div(int numerator,int denominator);

#endif
