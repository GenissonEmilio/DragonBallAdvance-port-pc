/* Test-only controller. Reads observations and returns ordinary button bits.
 * It never writes guest memory. Address hints from xy2_'s observational Lua
 * (https://tasvideos.org/UserFiles/Info/44092704218140697) were checked against
 * USA snapshots; the control policy below is independent code. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include "game_runtime.h"

static uint8_t *ewram;
static uint8_t *iwram;
void dbaa_policy_original_bind(uint8_t *external, uint8_t *internal, uint8_t *io);
void Dbaa_GameAudioBindMemory(uint8_t *external, uint8_t *internal, uint8_t *io) {
  ewram = external;
  iwram = internal;
  dbaa_policy_original_bind(external, internal, io);
}
uint16_t dbaa_policy_original_keys(void);
static FILE *input, *observations;
static unsigned last_keys = UINT_MAX, last_frame = UINT_MAX;
static unsigned stalled, jump_start = UINT_MAX, turn_until;
static unsigned combat_jump_until;
static int last_x, facing = 1;
static uint32_t last_target, ignored_target, ignored_tag;
static unsigned last_damage, ignore_until;
static int last_life;

static uint32_t read32(unsigned offset) {
  return (uint32_t)ewram[offset] | (uint32_t)ewram[offset + 1] << 8 |
         (uint32_t)ewram[offset + 2] << 16 | (uint32_t)ewram[offset + 3] << 24;
}
static int read16(unsigned offset) {
  return (int16_t)((unsigned)ewram[offset] | (unsigned)ewram[offset + 1] << 8);
}
static int absolute(int n) { return n < 0 ? -n : n; }
static unsigned internal16(unsigned o) { return iwram[o] | (unsigned)iwram[o + 1] << 8; }
static int active_object(uint32_t object) {
  unsigned task = internal16(0x2CD0);
  for (unsigned n = 0; task && task <= 0x7FEC && n < 128; ++n) {
    unsigned offset = internal16(task + 6);
    if ((internal16(task + 18) & 16) && 0x02000000u + offset * 4 == object) return 1;
    task = internal16(task + 4);
  }
  return 0;
}
static void finish(void) {
  if (input) fclose(input);
  if (observations) fclose(observations);
}
uint16_t display_get_keys(void) {
  unsigned frame = Dbaa_GameFrameCount();
  unsigned keys = (~dbaa_policy_original_keys()) & 1023u;
  if (last_frame == UINT_MAX) {
    input = fopen("policy_input.txt", "wb");
    observations = fopen("policy_observations.csv", "wb");
    if (!input || !observations) exit(2);
    fprintf(observations, "frame,x,y,vx,vy,param_20658,camera_x,camera_y,target_dx,target_dy,target_life,keys,stalled\n");
    atexit(finish);
  }
  int x = (int32_t)read32(0x205C4) / 256;
  int y = (int32_t)read32(0x205C8) / 256;
  int vx = read16(0x205CC), vy = read16(0x205CE);
  int camera_x = (int)(read32(0x29EE8) & 0xFFFFFF);
  int camera_y = (int)(read32(0x29EEC) & 0xFFFFFF);
  int dx = 0, dy = 0, hp = 0;
  uint32_t selected = 0, selected_tag = 0;
  int nearest = INT_MAX;
  for (unsigned i = 0; i < 11; ++i) {
    uint32_t pointer = read32(0x27E00 + i * 4);
    if (!pointer) break;
    if (pointer < 0x02000000u || pointer > 0x0203FF40u || !active_object(pointer)) continue;
    unsigned offset = pointer - 0x02000000u;
    if (read32(offset + 8) & 0x8000u) continue;
    int life = read16(offset + 0xB0);
    uint32_t tag = read32(offset + 0xA4);
    if (pointer == ignored_target && tag == ignored_tag && frame < ignore_until) continue;
    int ex = (int32_t)read32(offset + 0x1C) / 256;
    int ey = (int32_t)read32(offset + 0x20) / 256;
    int distance = absolute(ex - x) + absolute(ey - y);
    if (life > 0 && absolute(ex - x) < 150 && absolute(ey - y) < 100 && distance < nearest) {
      nearest = distance; dx = ex - x; dy = ey - y; hp = life;
      selected = pointer; selected_tag = tag;
    }
  }
  if (frame >= 2700) {
    if (frame != last_frame) stalled = x == last_x ? stalled + 1 : 0;
    if (selected != last_target || hp != last_life) last_damage = frame;
    /* The observed object list also contains non-combat objects. If repeated
     * attacks make no progress while standing still, try moving past that
     * candidate; do not alter its flags, life or task. */
    if (selected && frame - last_damage > 600) {
      ignored_target = selected; ignored_tag = selected_tag; ignore_until = frame + 1800;
      hp = 0;
    }
    last_target = selected; last_life = hp;
    if (hp) {
      int direction = dx < 0 ? -1 : 1;
      if (direction != facing) { facing = direction; turn_until = frame + 3; }
      if (frame % 96 == 24 && (dy < -8 || dy > 20)) combat_jump_until = frame + 23;
      keys = absolute(dx) > 30 || frame < turn_until ? (facing > 0 ? 16u : 32u) : 0u;
      if (dy < -8 || dy > 20) {
        unsigned phase = frame % 96;
        if (absolute(dx) > 8) keys = facing > 0 ? 16 : 32;
        if (phase >= 24 && phase < 47) keys |= 1;
        if (phase >= 48 && phase % 8 < 6) keys |= 2;
        if (phase >= 48 && dy < -16) keys |= 64;
        if (phase >= 48 && dy > 20) keys |= 128;
      } else {
        if (frame % 8 < 6) keys |= 2;
        if (absolute(dx) < 36 && frame % 180 < 2) keys |= 512;
      }
      if (frame < combat_jump_until)
        keys = (absolute(dx) > 8 ? (facing > 0 ? 16u : 32u) : 0u) | 1u;
    } else {
      facing = 1;
      keys = 16;
      if (jump_start == UINT_MAX && (stalled >= 12 || frame % 150 == 0)) jump_start = frame;
      if (jump_start != UINT_MAX) {
        unsigned phase = frame - jump_start;
        if (phase >= 20 && phase < 43) keys |= 1;
        if (phase >= 66 && phase < 70 && stalled > 40) keys = 32 | 1;
        if (phase >= 96) jump_start = UINT_MAX;
      }
    }
  }
  if (keys != last_keys) {
    /* Render N updates script input AFTER sampling KEYINPUT for N. Thus a
     * replay event at N-1 supplies the key observed at this boundary N. */
    fprintf(input, "%u %x\n", frame ? frame - 1 : 0, keys);
    last_keys = keys;
  }
  if (frame % 30 == 0)
    fprintf(observations, "%u,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%u,%u\n", frame,
            x, y, vx, vy, read16(0x20658), camera_x, camera_y, dx, dy, hp, keys, stalled);
  last_x = x;
  last_frame = frame;
  return (uint16_t)(~keys & 1023u);
}
