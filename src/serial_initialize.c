#include "services.h"
#include "serial.h"
extern DbaaU8 gSerialCodeA[],gSerialCodeB[];
extern const DbaaU8 gSerialCodeSourceA[],gSerialCodeSourceB[];
void Func_08113CE0(int mode)
{
    int i;
    IO16(0x04000208)=0;
    IO16(0x04000200)&=0xff3f;
    IO16(0x04000208)=1;
    IO16(0x04000134)=0;
    IO32(0x04000128)=0x2000;
    IO16(0x04000128)|=0x4003;
    { DbaaU32 zero=0; Bios_CpuSet(&zero,&gSerialState,0x0500007a); }
    Bios_CpuSet(gSerialCodeSourceA,gSerialCodeA,0x04000010);
    Bios_CpuSet(gSerialCodeSourceB,gSerialCodeB,0x04000048);
    gSerialState.mode=mode;
    gSerialState.word14=13;
    gSerialState.sendA=(DbaaU8 *)&gSerialState+0x60;
    gSerialState.sendB=(DbaaU8 *)&gSerialState+0x7c;
    for(i=0;i<4;i++) {
        gSerialState.receiveA[i]=(DbaaU8 *)&gSerialState+0x98+i*0x54;
        gSerialState.receiveB[i]=(DbaaU8 *)&gSerialState+0xb4+i*0x54;
        gSerialState.receiveC[i]=(DbaaU8 *)&gSerialState+0xd0+i*0x54;
    }
    IO16(0x04000208)=0;
    IO16(0x04000200)|=0x80;
    IO16(0x04000208)=1;
}
