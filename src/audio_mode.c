#include "services.h"
#include "audio.h"
void Sound_VSyncOff(void);
void Sound_SetFrequency(DbaaU32);
void Func_0810B2D0(DbaaU32 mode)
{
    struct SoundInfo *sound=gSoundInfoPointer;
    DbaaU32 temp;
    if(sound->lock!=0x68736d53) return;
    sound->lock++;
    temp=mode&0xff;
    if(temp) sound->reverb=temp&0x7f;
    temp=mode&0xf00;
    if(temp) {
        struct SoundChannel *channel;
        sound->channels=temp>>8;
        temp=12;
        channel=&sound->channel[0];
        while(temp!=0) {channel->status=0;temp--;channel++;}
    }
    temp=mode&0xf000;
    if(temp) sound->volume=temp>>12;
    temp=mode&0xb00000;
    if(temp) {
        temp=(temp&0x300000)>>14;
        (*(volatile DbaaU8 *)0x04000089)=((*(volatile DbaaU8 *)0x04000089)&0x3f)|temp;
    }
    temp=mode&0xf0000;
    if(temp) {Sound_VSyncOff();Sound_SetFrequency(temp);}
    sound->lock=0x68736d53;
}
