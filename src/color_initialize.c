#include "services.h"
void Func_08114BA4(void)
{
    DbaaU8 i;
    for(i=0; i<32; i++) {
        gColorComponents[0][i]=i;
        gColorComponents[1][i]=i<<5;
        gColorComponents[2][i]=i<<10;
    }
    gColorState=0;
}
