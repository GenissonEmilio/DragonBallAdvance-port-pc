#include "services.h"
#include "audio.h"
extern DbaaU8 gSoundMainBuffer[],gSoundInfo[],gCgbChannels[],gMusicMemory[];
void SoundMainRam(void);
void Sound_Initialize(void *);
void Sound_Extend(void *);
void MusicPlayer_Open(struct MusicPlayer *,void *,DbaaU32);
void Func_0810AD34(void)
{
    int i;
    Bios_CpuSet((void *)((DbaaU32)SoundMainRam&~1),gSoundMainBuffer,0x04000100);
    Sound_Initialize(gSoundInfo);
    Sound_Extend(gCgbChannels);
    Func_0810B2D0(0x0095fc00);
    for(i=0;i<(DbaaU16)(DbaaU32)&gMusicPlayerCount;i++) {
        struct MusicPlayer *player=gMusicPlayerTable[i].player;
        MusicPlayer_Open(player,gMusicPlayerTable[i].tracks,gMusicPlayerTable[i].count);
        player->priority=gMusicPlayerTable[i].priority;
        player->memory=gMusicMemory;
    }
}
