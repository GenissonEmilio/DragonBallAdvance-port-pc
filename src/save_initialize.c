#include "save_services.h"
DbaaU8 Func_08001538(void)
{
    DbaaU32 signature;
    DbaaU8 result=0;
    int c=0,b=0,a;
    a=Func_080016AC(&signature);
    if(signature!=0x9547424c) {
        b=Func_080015D0();c=Func_080017A0();
        Func_08001D00(2);gSaveGameState.byte1C=0;gSaveGameState.byte03=2;Func_08002100();
        Func_08001D00(1);gSaveGameState.byte1C=0;gSaveGameState.byte03=1;Func_08002100();
        Func_08001D00(0);gSaveGameState.byte1C=0;gSaveGameState.byte03=0;Func_08002100();
        result=2;
    } else if(gSaveHeader.half14==1) result=2;
    if(!a||!b||!c) result=1;
    else if(result!=2) result=0;
    return result;
}
