#ifndef DBAA_PORT_MUSIC_PLAYER_H
#define DBAA_PORT_MUSIC_PLAYER_H

#include <stdint.h>

/* Game data keeps its original 32-bit addresses. The host resolves memory and
 * binds routine addresses to C implementations; it need not execute ARM code.
 * Access widths are in bytes (1, 2 or 4), with little-endian integer values.
 * read/write also resolve GBA I/O addresses: preserve access width and order;
 * a host backend supplies device behavior rather than dereferencing that
 * address. call returns the semantic result for functions with a return value;
 * a void service's result is unspecified. Unused arguments are zero.
 * Polling reads of VCOUNT (0x04000006) must observe host clock progress;
 * Sound_SetFrequency waits to leave line 159, then reach it again.
 */
typedef struct DbaaMusicHost {
  void *user;
  uint32_t (*read)(void *user, uint32_t address, uint32_t width);
  void (*write)(void *user, uint32_t address, uint32_t value, uint32_t width);
  uint32_t (*call)(void *user, uint32_t target, uint32_t a0, uint32_t a1,
                   uint32_t a2);
} DbaaMusicHost;

void Dbaa_MusicPlayerUpdate(const DbaaMusicHost *host, uint32_t player);

#endif
