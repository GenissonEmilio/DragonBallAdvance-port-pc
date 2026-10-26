#ifndef DBAA_GAME_WINDOW_H
#define DBAA_GAME_WINDOW_H
#include <stdint.h>
int Dbaa_WindowOpen(void);
void Dbaa_WindowPresent(const uint32_t *pixels);
int Dbaa_WindowPoll(uint16_t *pressed);
void Dbaa_WindowPace(void);
void Dbaa_WindowClose(void);
#endif
