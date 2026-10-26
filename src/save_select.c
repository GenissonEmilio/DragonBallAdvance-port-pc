#include "save_services.h"
void Func_080030A0(void)
{
    DbaaU8 i;
    for(i=0;i<3;i++) {
        gSaveGameState.byte03=i;
        if(Func_08002328()!=0) break;
        if(i==2) {gSaveGameState.byte08=2;break;}
    }
}
