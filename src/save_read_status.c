/* Read the save header from EEPROM, with a fallback to its backup bank. */
#include "save_services.h"
int Func_08001BE4(void)
{
    struct SaveGameState *first=&gSaveGameState,*second=&gSaveGameStateBackup;
    struct SaveHeader *header=&gSaveHeader;
    DbaaU16 buffer[4];
    volatile DbaaU16 zero;
    DbaaU16 checksum=0;
    DbaaU8 flags=0;
    DbaaU16 x,y,z,error,i;
    register DbaaU8 *destination __asm__("r5");
    /* Empty GNU C constraints preserve the original register lifetimes.
     * They emit no machine instructions and do not alter the linked output. */
    __asm__("" : "+r"(checksum));
    {
        DbaaU16 *p=&x;
        __asm__("" : "+r"(flags) : "r"(p) : "r2","r3");
        *p=checksum;
    }
    y=checksum;z=checksum;error=0;
    if(gSystemFlags&0x100) return 0;
    first->checksum=checksum;first->byte02=flags;
    second->checksum=checksum;second->byte02=flags;
    header->checksum=checksum;header->byte02=flags;
    {zero=checksum;Bios_CpuSet(&zero,&buffer,0x01000004);}
    Func_080027C8(&x,&y,&z);
    destination=(DbaaU8 *)&buffer;__asm__("" : "+r"(destination));
    for(i=1;i<2;destination+=8,i++) {
        error=Func_081157C4(i,destination);
        if(error) break;
    }
    if(error) {
        destination=(DbaaU8 *)&buffer;
        for(i=gSaveEepromConfig->count>>1;i<(gSaveEepromConfig->count>>1)+1;destination+=8,i++) {
            if(Func_081157C4(i,destination)) break;
        }
    }
    first->checksum=buffer[0];first->byte02=buffer[1];
    second->checksum=buffer[0];second->byte02=buffer[1];
    header->checksum=buffer[0];header->byte02=buffer[1];
    Func_08003028(&x,&y,&z);
    return 1;
}
