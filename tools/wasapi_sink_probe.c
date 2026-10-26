/* Submit a previously ROM-validated raw PCM16 stereo stream to the game sink.
 */
#include "wasapi_sink.h"
#include <inttypes.h>
#include <stdio.h>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  FILE *file = fopen(argv[1], "rb");
  if (!file || !Dbaa_WasapiOpen()) {
    if (file)
      fclose(file);
    Dbaa_WasapiClose(NULL);
    return 1;
  }
  int16_t samples[2048];
  size_t bytes;
  int ok = 1;
  while ((bytes = fread(samples, 1, sizeof(samples), file))) {
    if ((bytes & 3) || !Dbaa_WasapiPush(samples, bytes / 4)) {
      ok = 0;
      break;
    }
  }
  if (ferror(file))
    ok = 0;
  fclose(file);
  DbaaWasapiStats stats;
  ok = Dbaa_WasapiClose(&stats) && ok;
  printf("{\"ok\":%s,\"supplied\":%" PRIu64 ",\"submitted\":%" PRIu64
         ",\"endpoint_empty\":%" PRIu64 ",\"queue_max\":%" PRIu64
         ",\"pcm_fnv1a64\":\"%016" PRIx64 "\",\"error\":%u}\n",
         ok ? "true" : "false", stats.supplied, stats.submitted,
         stats.endpoint_empty, stats.queue_max, stats.pcm_fnv1a64, stats.error);
  return ok ? 0 : 1;
}
