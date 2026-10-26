#include "services.h"
#include "task_memory.h"
#include "audio.h"
#include "serial.h"
static inline void ClearInputState(void){gInputResult=0;gInputMode=0;}
void Func_080FA048(void)
{
    DbaaU16 i;
    Tasks_DestroyPriorityRange(0,0xffff);
    gInitByte03003F74=gInitByte03003D00;
    gInitByte03006C20=0;
    gInitByte030065E8=gInitByte03003F10;
    Func_08114D70();Func_080010C4();
    {volatile DbaaU32 zero=0;DMA_START(&zero,gInputBufferA,0x85000005);DMA_WAIT();}
    {volatile DbaaU32 zero=0;DMA_START(&zero,gInputBufferB,0x85000014);DMA_WAIT();}
    ClearInputState();
    Func_08113CE0(0);Func_08000FDC();Func_08113C38();
    gGameHalf03002BEC=0x200;gGamePointer03002CB0=(void *)0x06014000;
    Func_08115618();Func_0810AEEC();
    IO16(0x04000208)=0;
    for(i=0;i<15;i++)gIrqHandlers[i]=gIrqDefaultHandlers[i];
    IO16(0x04000208)=1;
    gSystemFlags&=~0x400;
}
