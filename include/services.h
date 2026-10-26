#include "initialization.h"
#include "tasks.h"
extern DbaaU16 gColorComponents[3][32];
extern DbaaU32 gColorState;
struct HeapHeader { DbaaU32 next, size; };
extern struct HeapHeader gEwramHeap;
extern DbaaU16 gVramHeapMap[];
extern const void *gEepromConfig;
/* ROM configuration records selected by the EEPROM_V124 capacity routine. */
extern const DbaaU8 gEepromConfig4[], gEepromConfig64[];
extern int gFreeTaskIndex;
extern DbaaU32 gGameWord02029E40, gGameWord02029EB4, gGameWord02024774;
extern DbaaU16 gGameHalf02029E44;
extern DbaaU8 gGameStateBytes[];
extern DbaaU8 gGameData0202A0C0[];
void Func_080045A0(void);
void Func_08016538(void);
void Func_080A32DC(void);
void Func_080A6DF0(void);
void Func_080A7BA0(void);
void Func_080A3B88(void);
void Func_0810A084(void);
void Func_080010C4(void);
void Func_08000FDC(void);
/* Preserve the extra source, destination and control reads in these game services. */
#define DMA_START_READBACK(s,d,c) \
{ volatile DbaaU32 *dma=(volatile DbaaU32 *)0x040000D4; \
  dma[0]=(DbaaU32)(s); (void)dma[0]; dma[1]=(DbaaU32)(d); (void)dma[1]; \
  dma[2]=(c); (void)dma[2]; (void)dma[2]; }
