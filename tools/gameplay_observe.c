/* Test-only observation wrapper. Original input passes through unchanged. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "game_runtime.h"
static uint8_t *external;
static const uint8_t *internal;
static FILE *file;
uint16_t dbaa_policy_original_keys(void);
void dbaa_policy_original_bind(uint8_t *a, uint8_t *b, uint8_t *c);
void Dbaa_GameAudioBindMemory(uint8_t *a, uint8_t *b, uint8_t *c) {
  external = a;
  internal = b;
  dbaa_policy_original_bind(a, b, c);
}
static uint32_t word(unsigned o) {
  return (uint32_t)external[o] | (uint32_t)external[o + 1] << 8 |
         (uint32_t)external[o + 2] << 16 | (uint32_t)external[o + 3] << 24;
}
static void finish(void) { if (file) fclose(file); }
uint16_t display_get_keys(void) {
  uint16_t keys = dbaa_policy_original_keys();
  unsigned frame = Dbaa_GameFrameCount();
  if (!file) {
    file = fopen("observations.csv", "wb");
    if (!file) exit(2);
    fprintf(file, "frame,x256,y256,camera_x,camera_y,state_00,state_08,keys,rng\n");
    atexit(finish);
  }
  if (frame % 10 == 0)
    fprintf(file, "%u,%d,%d,%u,%u,%u,%u,%u,%u\n", frame,
            (int32_t)word(0x205C4), (int32_t)word(0x205C8), word(0x29EE8), word(0x29EEC),
            word(0x29F30), word(0x29F38), (unsigned)(~keys & 1023u),
            (uint32_t)internal[0x6C50] | (uint32_t)internal[0x6C51] << 8 |
            (uint32_t)internal[0x6C52] << 16 | (uint32_t)internal[0x6C53] << 24);
  return keys;
}
