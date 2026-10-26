#ifndef DBAA_WASAPI_SINK_H
#define DBAA_WASAPI_SINK_H
#include <stddef.h>
#include <stdint.h>
typedef struct {
  uint64_t supplied, submitted, pcm_fnv1a64, endpoint_empty, queue_max;
  uint32_t error;
  uint32_t render_error, push_wait_result, drain_wait_result;
  uint32_t last_padding, capacity;
  uint64_t render_wakes, queue_remaining;
  uint64_t first_empty_at_submitted, last_empty_at_submitted, empty_with_queued;
  uint32_t mmcss_enabled;
  uint64_t max_push_gap_us, max_gap_at_supplied, max_gap_queued;
  uint64_t max_render_gap_us, render_gap_at_submitted;
} DbaaWasapiStats;
int Dbaa_WasapiOpen(void);
int Dbaa_WasapiPush(const int16_t *stereo, size_t frames);
size_t Dbaa_WasapiQueued(void);
int Dbaa_WasapiClose(DbaaWasapiStats *stats);
#endif
