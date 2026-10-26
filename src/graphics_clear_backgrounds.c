#include "services.h"
struct ClearRects {DbaaU8 data[4][4];};
extern struct ClearRects gBgClearRects;
#undef DMA_FILL16
/* This routine reuses one halfword scratch cell for every fill. */
#define DMA_FILL16(v,d,c) \
{ DbaaU16 value=(v); void *dest=(d); fill16=value; DMA_START(&fill16,dest,(c)); }
extern DbaaU8 gBgClearValues[4];
int Graphics_ClearBackgrounds(void)
{
    DbaaU16 fill16;
    DbaaU8 bg=0, y;
    DbaaU16 pitch;
    DbaaU8 size;
    DbaaU8 *destination;
    int x;
    for(;bg<4;bg++) {
        if(gBgClearRects.data[bg][1]==gBgClearRects.data[bg][3]
           &&gBgClearRects.data[bg][0]==gBgClearRects.data[bg][2]) continue;
        {
            DbaaU16 target=gBgControlShadow[bg];
            DbaaU16 *base=(DbaaU16 *)0x06000000;
            target&=0x1f00;
            base+=target*4;
            destination=(DbaaU8 *)base;
        }
        y=gBgClearRects.data[bg][1];
        x=gBgClearRects.data[bg][0];
        if(bg>1 && (gDisplayControlShadow&3)) {
            destination+=x;
            size=gBgControlShadow[bg]>>14;
            pitch=16<<size;
            if(gBgClearRects.data[bg][3]==255) {
                DMA_FILL16(gBgClearValues[bg]|(gBgClearValues[bg]<<8),destination+y*pitch,
                           0x81000000|((gBgClearRects.data[bg][3]-y)*pitch/2));
            } else {
                for(;y<=gBgClearRects.data[bg][3];y++) {
                    DMA_FILL16(gBgClearValues[bg]|(gBgClearValues[bg]<<8),destination+y*pitch,
                               0x81000000|(((gBgClearRects.data[bg][2]-x+1)>>1)/2));
                }
            }
        } else {
            destination+=x*2;
            pitch=32;
            size=gBgControlShadow[bg]>>14;
            if((DbaaU8)(size-2)<=1)
                pitch=64;
            if(gBgClearRects.data[bg][2]==255) {
                DMA_FILL16(gBgClearValues[bg],destination+((int)pitch<<1)*y,
                           0x81000000|(((gBgClearRects.data[bg][3]-y)*pitch*2)>>1));
            } else {
                for(;y<=gBgClearRects.data[bg][3];y++) {
                    DMA_FILL16(gBgClearValues[bg],destination+y*((int)pitch<<1),
                               0x81000000|(gBgClearRects.data[bg][2]-x+1));
                }
            }
        }
        DMA_FILL32(0,&gBgClearRects.data[bg],0x85000001);
    }
    return 1;
}
