#include "services.h"
struct SaveGameState {
    DbaaU16 checksum;
    DbaaU8 byte02,byte03,byte04,byte05,byte06,byte07,byte08;
    DbaaU8 unknown09[0x13];
    DbaaU8 byte1C,unknown1D[7],byte24,bits25[7],unknown2C[8];
    DbaaU8 byte34,unknown35[3],byte38,unknown39;
    DbaaU16 half3A;DbaaU32 word3C;
    DbaaU8 unknown40[0x58];
};
struct SaveHeader {DbaaU16 checksum;DbaaU8 byte02,unknown03[0x11];DbaaU16 half14;DbaaU8 unknown16[0x2a];};
extern struct SaveGameState gSaveGameState,gSaveGameStateBackup;
extern struct SaveHeader gSaveHeader;
struct EepromConfig {DbaaU32 size;DbaaU16 count;};
extern const struct EepromConfig *gSaveEepromConfig;
int Func_080016AC(DbaaU32 *);
int Func_080015D0(void);
int Func_080017A0(void);
void Func_08001D00(int);
void Func_08002100(void);
void Func_08001D98(struct SaveGameState *,int);
void Func_08002DF8(struct SaveHeader *,int);
int Func_08002328(void);
void Func_08002940(void);
DbaaU16 Func_08002DA8(struct SaveGameState *);
void Func_080027C8(DbaaU16 *,DbaaU16 *,DbaaU16 *);
void Func_08003028(DbaaU16 *,DbaaU16 *,DbaaU16 *);
DbaaU16 Func_081157C4(DbaaU16,void *);
