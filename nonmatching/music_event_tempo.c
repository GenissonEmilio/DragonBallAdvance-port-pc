/* NONMATCHING ARM C: the SDK returns its byte in r3 and preserves r0/r1. */
#include "audio.h"
void Music_ReadCommandFiltered(void *player, DbaaU8 *track);
void MusicEvent_Tempo(DbaaU8 *inputPlayer, DbaaU8 *inputTrack) {
  register DbaaU8 *player __asm__("r0");
  register DbaaU8 *track __asm__("r1");
  register DbaaU32 scale __asm__("r2"), value __asm__("r3");
  Music_ReadCommandFiltered(inputPlayer, inputTrack);
  __asm__ volatile("" : "=r"(player), "=r"(track), "=r"(value));
  value <<= 1;
  *(DbaaU16 *)(player + 0x1C) = value;
  scale = *(DbaaU16 *)(player + 0x1E);
  value *= scale;
  value >>= 8;
  *(DbaaU16 *)(player + 0x20) = value;
}
