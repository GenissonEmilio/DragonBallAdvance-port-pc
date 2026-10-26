#include "services.h"
DbaaU16 Func_081156FC(DbaaU16 value)
{
    DbaaU16 result=0;
    if(value==4) gEepromConfig=gEepromConfig4;
    else if(value==64) gEepromConfig=gEepromConfig64;
    else { gEepromConfig=gEepromConfig4; result=1; }
    return result;
}
