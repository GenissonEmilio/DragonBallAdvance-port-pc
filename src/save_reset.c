#include "save_services.h"
void Func_08001D00(int mode)
{
    DbaaU8 first=gSaveGameState.byte1C,second=gSaveGameStateBackup.byte1C;
    DbaaU16 header=gSaveHeader.half14&0xff;
    {volatile DbaaU16 zero=0;Bios_CpuSet(&zero,&gSaveGameState,0x0100004c);}
    gSaveGameState.byte1C=first;
    Func_08001D98(&gSaveGameState,mode);
    {volatile DbaaU16 zero=0;Bios_CpuSet(&zero,&gSaveGameStateBackup,0x0100004c);}
    gSaveGameStateBackup.byte1C=second;
    Func_08001D98(&gSaveGameStateBackup,mode);
    {volatile DbaaU16 zero=0;Bios_CpuSet(&zero,&gSaveHeader,0x01000020);}
    gSaveHeader.half14=header;
    Func_08002DF8(&gSaveHeader,mode);
}
