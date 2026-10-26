#ifndef DBAA_PORT_AUDIO_HELPERS_H
#define DBAA_PORT_AUDIO_HELPERS_H

#include "music_player.h"

uint32_t Dbaa_AudioClear64(const DbaaMusicHost *, uint32_t destination);
uint32_t Dbaa_AudioUnlinkChannel(const DbaaMusicHost *, uint32_t channel);
uint32_t Dbaa_AudioFilterAddress(const DbaaMusicHost *, uint32_t source,
                                 uint32_t value);
uint32_t Dbaa_AudioReadByte(const DbaaMusicHost *, uint32_t source);
uint32_t Dbaa_SoundCopyCommandTable(const DbaaMusicHost *,
                                    uint32_t destination);
uint32_t Dbaa_MusicEventFine(const DbaaMusicHost *, uint32_t player,
                             uint32_t track);
uint32_t Dbaa_MusicTrackStop(const DbaaMusicHost *, uint32_t player,
                             uint32_t track);
uint32_t Dbaa_MusicFadeOutBody(const DbaaMusicHost *, uint32_t player);
uint32_t Dbaa_MusicTrackVolumePitch(const DbaaMusicHost *, uint32_t player,
                                    uint32_t track);
uint32_t Dbaa_MusicCalculateFrequency(const DbaaMusicHost *, uint32_t wave,
                                      uint32_t key, uint32_t fine);
uint32_t Dbaa_CgbCalculateFrequency(const DbaaMusicHost *, uint32_t channel,
                                    uint32_t key, uint32_t fine);
uint32_t Dbaa_MusicClearModulation(const DbaaMusicHost *, uint32_t player,
                                   uint32_t track);
uint32_t Dbaa_SoundUpdateTrack(const DbaaMusicHost *, uint32_t duration,
                               uint32_t player, uint32_t track);
uint32_t Dbaa_MusicEventEndTie(const DbaaMusicHost *, uint32_t player,
                               uint32_t track);
uint32_t Dbaa_MusicReadCommandByte(const DbaaMusicHost *, uint32_t player,
                                   uint32_t track);
uint32_t Dbaa_MusicEventLfoSpeed(const DbaaMusicHost *, uint32_t player,
                                 uint32_t track);
uint32_t Dbaa_MusicEventModDepth(const DbaaMusicHost *, uint32_t player,
                                 uint32_t track);
uint32_t Dbaa_MusicEventMemoryAccess(const DbaaMusicHost *, uint32_t player,
                                     uint32_t track);
uint32_t Dbaa_MusicEventExtended(const DbaaMusicHost *, uint32_t player,
                                 uint32_t track);
uint32_t Dbaa_MusicEventExtendedEnd(const DbaaMusicHost *, uint32_t player,
                                    uint32_t track);
uint32_t Dbaa_MusicEventWave(const DbaaMusicHost *, uint32_t player,
                             uint32_t track);
uint32_t Dbaa_MusicEventGoto(const DbaaMusicHost *, uint32_t player,
                             uint32_t track);

/* Resolve known audio routines in C, delegating only unresolved targets to
 * host->call. Both even entry addresses and Thumb pointers are accepted. */
uint32_t Dbaa_MusicEventPattern(const DbaaMusicHost *, uint32_t player,
                                uint32_t track);
uint32_t Dbaa_MusicEventPatternEnd(const DbaaMusicHost *, uint32_t player,
                                   uint32_t track);
uint32_t Dbaa_MusicEventRepeat(const DbaaMusicHost *, uint32_t player,
                               uint32_t track);
uint32_t Dbaa_MusicReadCommandFiltered(const DbaaMusicHost *, uint32_t player,
                                       uint32_t track);
uint32_t Dbaa_MusicEventPriority(const DbaaMusicHost *, uint32_t player,
                                 uint32_t track);
uint32_t Dbaa_MusicEventTempo(const DbaaMusicHost *, uint32_t player,
                              uint32_t track);
uint32_t Dbaa_MusicEventKeyShift(const DbaaMusicHost *, uint32_t player,
                                 uint32_t track);
uint32_t Dbaa_AudioCall(const DbaaMusicHost *, uint32_t target, uint32_t a0,
                        uint32_t a1, uint32_t a2);

uint32_t Dbaa_MusicEventVoice(const DbaaMusicHost *, uint32_t player,
                              uint32_t track);
uint32_t Dbaa_MusicEventVolume(const DbaaMusicHost *, uint32_t player,
                               uint32_t track);
uint32_t Dbaa_MusicEventPan(const DbaaMusicHost *, uint32_t player,
                            uint32_t track);
uint32_t Dbaa_MusicEventPitchBend(const DbaaMusicHost *, uint32_t player,
                                  uint32_t track);
uint32_t Dbaa_MusicEventBendRange(const DbaaMusicHost *, uint32_t player,
                                  uint32_t track);

uint32_t Dbaa_MusicEventLfoDelay(const DbaaMusicHost *, uint32_t player,
                                 uint32_t track);

uint32_t Dbaa_MusicEventModType(const DbaaMusicHost *, uint32_t player,
                                uint32_t track);

uint32_t Dbaa_MusicEventTune(const DbaaMusicHost *, uint32_t player,
                             uint32_t track);

uint32_t Dbaa_MusicEventPort(const DbaaMusicHost *, uint32_t player,
                             uint32_t track);

uint32_t Dbaa_SoundVSyncOn(const DbaaMusicHost *);
uint32_t Dbaa_SoundSetFrequency(const DbaaMusicHost *, uint32_t mode);
uint32_t Dbaa_SoundVSyncOff(const DbaaMusicHost *);
uint32_t Dbaa_SoundMode(const DbaaMusicHost *, uint32_t mode);
uint32_t Dbaa_SoundInitialize(const DbaaMusicHost *, uint32_t sound);
uint32_t Dbaa_SoundExtend(const DbaaMusicHost *, uint32_t channels);
uint32_t Dbaa_CgbStop(const DbaaMusicHost *, uint32_t channel);
uint32_t Dbaa_CgbUpdateVolume(const DbaaMusicHost *, uint32_t channel);
uint32_t Dbaa_CgbUpdate(const DbaaMusicHost *);
uint32_t Dbaa_SoundMain(const DbaaMusicHost *);
uint32_t Dbaa_AudioInitialize(const DbaaMusicHost *);
uint32_t Dbaa_AudioMain(const DbaaMusicHost *);
uint32_t Dbaa_MusicPlayerOpen(const DbaaMusicHost *, uint32_t player,
                              uint32_t tracks, uint32_t count);
uint32_t Dbaa_MusicStartSong(const DbaaMusicHost *, uint32_t song);
uint32_t Dbaa_MusicPlayerStart(const DbaaMusicHost *, uint32_t player,
                               uint32_t header);
uint32_t Dbaa_MusicPlayerStop(const DbaaMusicHost *, uint32_t player);
uint32_t Dbaa_MusicStopAll(const DbaaMusicHost *);

#endif
