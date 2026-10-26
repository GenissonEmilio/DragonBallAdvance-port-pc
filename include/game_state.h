#ifndef DBAA_GAME_STATE_H
#define DBAA_GAME_STATE_H

typedef unsigned char DbaaU8;
typedef signed char DbaaS8;
typedef unsigned short DbaaU16;
typedef signed short DbaaS16;
typedef unsigned int DbaaU32;

/* Partial view of the USA state block at 0x02029F30.
 * Field names describe offsets until their gameplay meaning is established.
 */
struct DbaaGameState
{
    DbaaU8 unknown00[2];
    DbaaU8 byte02;
    DbaaU8 unknown03[5];
    DbaaU8 byte08;
    DbaaU8 unknown09[7];
    DbaaU32 word10;
    DbaaU32 word14;
    DbaaU8 unknown18[0x0A];
    DbaaU8 flag22;
};

typedef char DbaaU32MustHaveFourBytes[(sizeof(DbaaU32) == 4) ? 1 : -1];

extern struct DbaaGameState gDbaaGameState;

void State_IncrementWord10IfFlag22(void);

#endif
