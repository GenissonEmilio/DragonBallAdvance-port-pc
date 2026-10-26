#ifndef DBAA_GRAPHICS_H
#define DBAA_GRAPHICS_H

#include "runtime.h"
#include "hardware.h"

extern DbaaU8 gGraphicsByte03002BF0;
extern DbaaU8 gGraphicsByte030065E0;
extern DbaaU8 gGraphicsByte03002CB8;
extern DbaaU8 gGraphicsByte03002C54;
extern DbaaU8 gGraphicsByte03003F80;
extern DbaaU8 gGraphicsByte03003B30;
extern DbaaU8 gGraphicsByte03006C30;
extern DbaaU8 gGraphicsByte03002BD0;
struct DbaaSpriteOffset
{
    DbaaS16 x, y;
};
extern struct DbaaSpriteOffset gSpriteOffset;
extern DbaaU16 gBgControlShadow[];
extern DbaaU16 gWindowShadow[];
extern DbaaU16 gBlendShadow[];
struct DbaaBgAffine
{
    DbaaS16 pa, pb, pc, pd;
    DbaaU32 x, y;
};
extern struct DbaaBgAffine gBgAffineShadow[];
extern DbaaU16 gBgScrollShadow[];
extern DbaaU8 gBgPaletteBuffer[];
extern DbaaU8 gObjPaletteBuffer[];
extern DbaaU8 gOamBuffer[];
extern DbaaU8 gOamBufferAlternate[];
extern DbaaU8 *gScanlineWriteBuffer;
extern DbaaU8 *gScanlineReadBuffer;
extern DbaaU8 gScanlineByte02000518;
extern void *gScanlineDmaDestination;

typedef void (*DbaaPaletteCallback)(void *palette, DbaaU8 offset, DbaaU16 count);
extern DbaaPaletteCallback gPaletteCallback;
void Graphics_LoadBgPalette(const void *palette, DbaaU8 offset, DbaaU32 count);
void Graphics_LoadObjPalette(const void *palette, DbaaU8 offset, DbaaU32 count);
/* Original BX r3 bridge: its fourth argument holds the three-argument callback. */
void Palette_CallCallback(void *palette, DbaaU8 offset, DbaaU16 count,
                          DbaaPaletteCallback callback);

void Bios_CpuFastSet(const void *source, void *destination, DbaaU32 control);
void Graphics_ProcessOam(void);
int Graphics_ClearBackgrounds(void);
extern int (*const gGraphicsCallbacks[])(void);
extern void (*gGraphicsFrameCallbacks[])(void);

#endif
