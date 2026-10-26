#ifndef DBAA_AUDIO_RUNTIME_H
#define DBAA_AUDIO_RUNTIME_H
#include "music_player.h"
#include <stddef.h>
#include <stdint.h>

#define DBAA_CPU_HZ 16777216u
#define DBAA_LINE_CYCLES 1232u
#define DBAA_FRAME_CYCLES 280896u
#define DBAA_OUTPUT_HZ 48000u
#define DBAA_PCM_MAX 704u
#define DBAA_AUDIO_RING 16384u
/* The ROM's 970-entry table ends at its shared empty header, 0x08A6AEB8. */
#define DBAA_SONG_COUNT 970u

typedef struct DbaaAudioRuntime DbaaAudioRuntime;
typedef void (*DbaaBusObserver)(void *, uint32_t write, uint32_t address,
                                uint32_t width, uint32_t value);
typedef struct DbaaAudioStats {
  uint64_t frames, source_samples, converted_samples, consumed_samples;
  uint64_t underrun_samples, overflow_samples, max_queued, cycles;
  uint64_t faults, cgb_active_frames;
} DbaaAudioStats;
typedef struct DbaaPcmBlock {
  uint32_t count, playing_offset, produced_offset, timer_ticks;
  uint8_t right[DBAA_PCM_MAX], left[DBAA_PCM_MAX];
  uint8_t produced_right[DBAA_PCM_MAX], produced_left[DBAA_PCM_MAX];
} DbaaPcmBlock;

/* Audio host only. No CPU interpreter or full-game frame loop. */
DbaaAudioRuntime *Dbaa_AudioRuntimeCreate(const uint8_t *rom, size_t size);
void Dbaa_AudioRuntimeDestroy(DbaaAudioRuntime *);
int Dbaa_AudioRuntimeInitialize(DbaaAudioRuntime *);
int Dbaa_AudioRuntimeFrame(DbaaAudioRuntime *);
int Dbaa_AudioRuntimeMode(DbaaAudioRuntime *, unsigned index);
int Dbaa_AudioRuntimeSuspend(DbaaAudioRuntime *, int suspend);
int Dbaa_AudioRuntimeDemo(DbaaAudioRuntime *);
int Dbaa_AudioRuntimeStartSong(DbaaAudioRuntime *, unsigned song);
int Dbaa_AudioRuntimeStopPlayer(DbaaAudioRuntime *, unsigned player_index);
int Dbaa_AudioRuntimeStopAll(DbaaAudioRuntime *);
void Dbaa_AudioRuntimeGain(DbaaAudioRuntime *, unsigned gain_q8);
size_t Dbaa_AudioRuntimeRead(DbaaAudioRuntime *, int16_t *stereo,
                             size_t frames);
size_t Dbaa_AudioRuntimeQueued(const DbaaAudioRuntime *);
void Dbaa_AudioRuntimeStats(const DbaaAudioRuntime *, DbaaAudioStats *);
void Dbaa_AudioRuntimeBlock(const DbaaAudioRuntime *, DbaaPcmBlock *);
void Dbaa_AudioRuntimeObserve(DbaaAudioRuntime *, DbaaBusObserver, void *);
size_t Dbaa_AudioRuntimeClockTrace(const DbaaAudioRuntime *, uint8_t *, size_t);
int Dbaa_AudioRuntimeMemory(DbaaAudioRuntime *, uint32_t address, void *,
                            size_t bytes, int write);
const char *Dbaa_AudioRuntimeError(const DbaaAudioRuntime *);
/* Behavioral counterpart of ROM 0x0810A6D8. Not a new GBA matching target. */
void Dbaa_AudioVBlank(const DbaaMusicHost *);
/* Exact rational deadline, independent of frame-to-frame Windows wake jitter.
 */
uint64_t Dbaa_AudioDeadline(uint64_t frame, uint64_t qpc_frequency);
#endif
