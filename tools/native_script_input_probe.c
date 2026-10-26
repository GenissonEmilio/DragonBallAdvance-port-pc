/* Test the actual display input script API before each VBlank sample. */
#include "gba/gba_runtime.h"
#include "gba/display.h"
#include <stdio.h>
int main(int n, char **v) {
  if (n != 3) return 2;
  char *args[] = {v[0], v[1], "--headless", "--input", v[2]};
  display_parse_args(5, args);
  gba_init(v[1]);
  for (unsigned i = 1; i <= 12; ++i) {
    unsigned a = (~display_get_keys()) & 1023u;
    unsigned b = (~display_get_keys()) & 1023u;
    printf("%u %u %u\n", i, a, b);
    display_render_frame();
  }
  gba_shutdown();
  return 0;
}
