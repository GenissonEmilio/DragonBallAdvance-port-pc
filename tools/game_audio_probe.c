/* Private RAM bus for exercising the real game audio consumer in isolation. */
#include "game_audio.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
static uint8_t external_ram[0x40000], internal_ram[0x8000], io_memory[0x400];
uint8_t *ewram = external_ram, *iwram = internal_ram, *io_regs = io_memory;

int Dbaa_GameAudioProbeMemory(uint32_t address, void *data, size_t bytes,
                              int write) {
  Dbaa_GameAudioBindMemory(ewram, iwram, io_regs);
  uint8_t *base = NULL;
  uint32_t offset = 0;
  size_t size = 0;
  switch (address >> 24) {
  case 2:
    base = ewram;
    offset = address - 0x02000000;
    size = sizeof(external_ram);
    break;
  case 3:
    base = iwram;
    offset = address - 0x03000000;
    size = sizeof(internal_ram);
    break;
  case 4:
    base = io_regs;
    offset = address - 0x04000000;
    size = sizeof(io_memory);
    break;
  default:
    return 0;
  }
  if (!data || bytes > size || offset > size - bytes)
    return 0;
  if (write)
    memcpy(base + offset, data, bytes);
  else
    memcpy(data, base + offset, bytes);
  return 1;
}
