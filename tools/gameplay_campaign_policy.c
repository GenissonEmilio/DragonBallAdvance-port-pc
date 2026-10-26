/* Native adapter for the read-only test controller. */
#include <stdio.h>
#include <stdlib.h>
#include "game_runtime.h"
#include "campaign_controller.h"
static const uint8_t *external, *internal;
static FILE *input, *observations;
static unsigned last_keys = UINT_MAX;
uint16_t dbaa_policy_original_keys(void);
void dbaa_policy_original_bind(uint8_t *, uint8_t *, uint8_t *);
void Dbaa_GameAudioBindMemory(uint8_t *a, uint8_t *b, uint8_t *c) {
  external = a; internal = b;
  dbaa_policy_original_bind(a, b, c);
}
static void finish(void) { if (input) fclose(input); if (observations) fclose(observations); }
uint16_t display_get_keys(void) {
  unsigned frame = Dbaa_GameFrameCount(), original = (~dbaa_policy_original_keys()) & 1023u;
  unsigned keys = Dbaa_TestCampaignKeys(external, internal, frame, original);
  if (!input) {
    input = fopen("policy_input.txt", "wb"); observations = fopen("policy_observations.csv", "wb");
    if (!input || !observations) exit(2);
    fprintf(observations, "frame,x,y,vx,vy,target_x,target_y,target_hp,climbing,keys\n");
    atexit(finish);
  }
  if (keys != last_keys) { fprintf(input, "%u %x\n", frame ? frame - 1 : 0, keys); last_keys = keys; }
  if (frame % 10 == 0)
    fprintf(observations, "%u,%d,%d,%d,%d,%d,%d,%d,%d,%u\n", frame,
            (int32_t)test_word(external, 0x205C4)/256, (int32_t)test_word(external, 0x205C8)/256,
            test_half(external, 0x205CC), test_half(external, 0x205CE),
            dbaa_test_controller.target_x, dbaa_test_controller.target_y,
            dbaa_test_controller.target_hp, dbaa_test_controller.climbing, keys);
  return (uint16_t)(~keys & 1023u);
}
