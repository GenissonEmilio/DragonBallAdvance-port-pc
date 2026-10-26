#ifndef DBAA_AUDIO_H
#define DBAA_AUDIO_H

#include "game_state.h"

struct MusicPlayer;
struct MusicTrack;
struct DbaaSongHeader {
  DbaaU8 trackCount, blockCount, priority, mode;
  const void *voicegroup;
  const DbaaU8 *trackData[1];
};
struct SoundChannel {
  DbaaU8 status, type;
  DbaaU8 unknown02[0x2A];
  struct MusicTrack *track;
  DbaaU8 unknown30[4];
  struct SoundChannel *next;
  DbaaU8 unknown38[8];
};
struct MusicTrack {
  DbaaU8 status, wait, unknown02[5], runningStatus;
  DbaaS8 calculatedKey;
  DbaaU8 calculatedPitch;
  DbaaS8 keyShift, keyShiftPublic, tune;
  DbaaU8 pitchPublic;
  DbaaS8 bend;
  DbaaU8 bendRange, right, left, volume, volumePublic;
  DbaaS8 pan, panPublic, modulation;
  DbaaU8 modDepth, modType, lfoSpeed, lfoPhase, unknown1B, lfoDelayCounter;
  DbaaU8 unknown1D[3];
  struct SoundChannel *channel;
  DbaaU8 unknown24[0x1C];
  const DbaaU8 *command;
  DbaaU8 unknown44[12];
};
/* Partial player view: only fields accessed by the reconstructed routines. */
struct MusicPlayer {
  const struct DbaaSongHeader *song;
  DbaaU32 status;
  DbaaU8 trackCount, songPriority, unknown0A, priority;
  DbaaU32 clock;
  DbaaU8 unknown10[8];
  void *memory;
  DbaaU16 tempo, tempoScale, tempoInterval, tempoCounter, fadeInterval;
  DbaaU16 fadeCounter, fadeLevel, unknown2A;
  struct MusicTrack *tracks;
  const void *voicegroup;
  DbaaU32 lock;
  void (*nextPlayerMain)(struct MusicPlayer *);
  struct MusicPlayer *nextPlayer;
};
struct MusicPlayerEntry {
  struct MusicPlayer *player;
  void *tracks;
  DbaaU8 count, unknown09;
  DbaaU16 priority;
};
struct SoundInfo {
  DbaaU32 lock;
  DbaaU8 unknown04, reverb, channels, volume;
  DbaaU8 frequency, unknown09[2], pcmFrames, maxLines, unknown0D[3];
  DbaaU32 samplesPerFrame, sampleRate, sampleReciprocal;
  void *cgbChannels;
  void (*playerMain)(struct MusicPlayer *);
  struct MusicPlayer *firstPlayer;
  void (*cgbMain)(void);
  void (*stopCgb)(DbaaU8);
  void (*callback30)(void);
  void (**commands)(void);
  void (*callback38)(void), (*callback3C)(void);
  DbaaU8 unknown40[0x10];
  struct SoundChannel channel[12];
};
extern const struct MusicPlayerEntry gMusicPlayerTable[];
/* Absolute linker symbol with value 4: its address is the player count. */
extern const DbaaU32 gMusicPlayerCount;
extern struct SoundInfo *gSoundInfoPointer;
struct DbaaSongEntry {
  const void *header;
  DbaaU16 player, unknown06;
};
extern const struct DbaaSongEntry gSongTable[];
void Music_StartSong(DbaaU16 song);
void MusicPlayer_Start(struct MusicPlayer *player, const void *song);
void Func_0810AEEC(void);
void MusicPlayer_Stop(struct MusicPlayer *player);
void MusicTrack_Stop(struct MusicPlayer *player, struct MusicTrack *track);
void MusicPlayer_Open(struct MusicPlayer *player, void *tracks, DbaaU32 count);
void MusicPlayer_Clear(struct MusicPlayer *player);
void MusicPlayer_Update(struct MusicPlayer *player);
extern void (*gMusicPlayerClearCallback)(struct MusicPlayer *);
extern const DbaaU16 gSoundSamplesPerFrame[];
void Sound_VSyncOff(void);
void Sound_VSyncOn(void);
void Sound_SetFrequency(DbaaU32 mode);

void Sound_Initialize(void *data);
void Sound_Extend(void *channels);
void Sound_Dummy(void);
void Cgb_Stop(DbaaU8 channel);
int Cgb_CalculateFrequency(DbaaU8 channel, DbaaU8 key, DbaaU8 fine);
void Cgb_UpdateVolume(DbaaU8 *channel);
void Cgb_Update(void);
void Music_FadeOutBody(struct MusicPlayer *player);
void MusicTrack_UpdateVolumePitch(struct MusicPlayer *player,
                                 struct MusicTrack *track);
/* SDK helper: consumes one byte and leaves its result in r3, not a C return. */
void Music_ReadCommandByte(void *player, DbaaU8 *track);
void Music_ClearModulation(void *player, DbaaU8 *track);
void MusicEvent_LfoSpeed(void *player, DbaaU8 *track);
void MusicEvent_ModDepth(void *player, DbaaU8 *track);
#endif
