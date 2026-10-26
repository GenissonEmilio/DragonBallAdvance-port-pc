#ifndef DBAA_GAME_AUDIO_H
#define DBAA_GAME_AUDIO_H
#include <stddef.h>
#include <stdint.h>
void Dbaa_GameAudioBindMemory(uint8_t *external, uint8_t *internal,
                              uint8_t *io);
int Dbaa_GameAudioInit(int device_enabled);
int Dbaa_GameAudioAdvance(uint32_t cycles);
int Dbaa_GameAudioQueueDepth(size_t *frames);
int Dbaa_GameAudioWrite(uint32_t offset, uint32_t value, unsigned width);
void Dbaa_GameAudioVBlank(void);
void Dbaa_GameAudioClose(void);
const char *Dbaa_GameAudioError(void);
#endif
