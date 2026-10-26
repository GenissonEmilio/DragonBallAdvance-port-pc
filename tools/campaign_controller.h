/* Test-only, read-only observation controller. Outputs ordinary button bits.
 * No ROM, RAM, health, inventory, save or game-state writes. */
#ifndef DBAA_TEST_CAMPAIGN_CONTROLLER_H
#define DBAA_TEST_CAMPAIGN_CONTROLLER_H
#include <stdint.h>
#include <limits.h>

typedef struct {
  unsigned jump_start, last_frame, stalled, turn_until, run_pulse_start, target_moved_until;
  int last_x, facing, climb_side, climb_x, climb_y;
  uint32_t target;
  int target_x, target_y, target_hp, climbing;
} DbaaTestCampaignController;
static DbaaTestCampaignController dbaa_test_controller = { .jump_start = UINT_MAX, .run_pulse_start = UINT_MAX, .facing = 1 };
static uint32_t test_word(const uint8_t *a, unsigned o) {
  return (uint32_t)a[o] | (uint32_t)a[o+1] << 8 | (uint32_t)a[o+2] << 16 | (uint32_t)a[o+3] << 24;
}
static int test_half(const uint8_t *a, unsigned o) { return (int16_t)(a[o] | (unsigned)a[o+1] << 8); }
static int test_abs(int x) { return x < 0 ? -x : x; }
static int test_active(const uint8_t *iwram, uint32_t object) {
  unsigned task = (uint16_t)test_half(iwram, 0x2CD0);
  for (unsigned i = 0; task && task <= 0x7FEC && i < 128; ++i) {
    unsigned offset = (uint16_t)test_half(iwram, task + 6);
    if ((test_half(iwram, task + 18) & 16) && 0x02000000u + offset * 4 == object) return 1;
    task = (uint16_t)test_half(iwram, task + 4);
  }
  return 0;
}
static unsigned Dbaa_TestCampaignKeys(const uint8_t *ram, const uint8_t *iwram,
                                      unsigned frame, unsigned original) {
  DbaaTestCampaignController *s = &dbaa_test_controller;
  if (frame < 2700) return original;
  int x = (int32_t)test_word(ram, 0x205C4) / 256;
  int y = (int32_t)test_word(ram, 0x205C8) / 256;
  int vy = test_half(ram, 0x205CE);
  int vx = test_half(ram, 0x205CC);
  if (frame != s->last_frame) s->stalled = x == s->last_x ? s->stalled + 1 : 0;
  s->last_frame = frame; s->last_x = x;
  int nearest = INT_MAX, ex = 0, ey = 0, hp = 0;
  uint32_t selected = 0;
  for (unsigned i = 0; i < 11; ++i) {
    uint32_t p = test_word(ram, 0x27E00 + i * 4);
    if (!p) break;
    if (p < 0x02000000u || p > 0x0203FF40u || !test_active(iwram, p)) continue;
    unsigned o = p - 0x02000000u;
    if (test_word(ram, o + 8) & 0x8000u) continue;
    int life = test_half(ram, o + 0xB0);
    int ox = (int32_t)test_word(ram, o + 0x1C) / 256;
    int oy = (int32_t)test_word(ram, o + 0x20) / 256;
    int distance = test_abs(ox - x) + test_abs(oy - y);
    /* One-HP objects observed in this list include props/projectiles. */
    if (life > 1 && test_abs(ox-x) < 600 && test_abs(oy-y) < 240 && distance < nearest) {
      nearest = distance; selected = p; ex = ox; ey = oy; hp = life;
    }
  }
  if (selected != s->target) {
    s->climb_side = x >= ex ? 1 : -1;
    s->target_moved_until = 0;
  } else if (test_abs(ey - s->target_y) > 1) s->target_moved_until = frame + 120;
  s->target = selected; s->target_x = ex; s->target_y = ey; s->target_hp = hp;
  if (s->jump_start != UINT_MAX) {
    unsigned elapsed = frame - s->jump_start;
    if (elapsed >= 96 || (elapsed > 25 && vy == 0)) s->jump_start = UINT_MAX;
    else {
      unsigned keys = elapsed < 23 ? 1u : 0u;
      int destination = s->climbing ? s->climb_x : (hp ? ex : x + 100);
      if (!s->climbing || y <= s->climb_y + 24 || elapsed >= 45)
        if (test_abs(destination - x) > 8) keys |= destination > x ? 16u : 32u;
      if (elapsed >= 25 && hp && test_abs(ex-x) < 95 && test_abs(ey-y) < 120 && elapsed % 8 < 6) {
        keys |= 2;
        if (ey-y < -20) keys |= 64;
        else if (ey-y > 20) keys |= 128;
      }
      return keys;
    }
  }
  if (hp) {
    int dx = ex-x, dy = ey-y;
    /* Walk off a ledge to a lower enemy instead of attacking empty air. */
    if (dy > 35 && vy == 0) return dx < 0 ? 32u : 16u;
    if (dy < -70 && vy == 0 && frame >= s->target_moved_until) {
      int stage = ex + s->climb_side * 64;
      if (test_abs(stage - x) > 8) return stage > x ? 16u : 32u;
      s->jump_start = frame; s->climbing = 1; s->climb_x = ex; s->climb_y = ey;
      return 1;
    }
    int facing = dx < 0 ? -1 : 1;
    if (facing != s->facing) { s->facing = facing; s->turn_until = frame + 3; }
    unsigned keys = test_abs(dx) > 24 || frame < s->turn_until ? (facing > 0 ? 16u : 32u) : 0;
    if (test_abs(dx) < 45 && test_abs(dy) < 45 && frame % 8 < 6 && frame >= s->turn_until) keys |= 2;
    if (hp >= 50 && test_abs(dx) < 64 && test_abs(dy) < 40 && frame % 180 == 1)
      keys = (facing > 0 ? 16u : 32u) | 0x300u;
    if (test_abs(dx) < 120 && dy < -25 && frame % 100 == 0) {
      s->jump_start = frame; s->climbing = 0;
      return (keys & ~2u) | 1;
    }
    if (dy < -25 && (keys & 2)) keys |= 64;
    if (dy > 25 && (keys & 2)) keys |= 128;
    return keys;
  }
  /* Ordinary running jump at the observed gap in the second map section.
   * Double-tapping right enables the game's run; walking cannot span it. */
  if (vy == 0 && vx < 700) {
    if (s->run_pulse_start == UINT_MAX) s->run_pulse_start = frame;
    unsigned phase = frame - s->run_pulse_start;
    if (phase < 4) return phase == 0 || phase == 2 ? 0u : 16u;
    if (phase > 40) s->run_pulse_start = UINT_MAX;
  }
  if (vy == 0 && y >= 480 && y <= 510 && x >= 864 && x < 892) {
    s->jump_start = frame; s->climbing = 0;
    return 17;
  }
  if (s->stalled >= 12 || frame % 150 == 0) {
    s->jump_start = frame; s->climbing = 0;
    return 17;
  }
  return 16;
}
#endif
