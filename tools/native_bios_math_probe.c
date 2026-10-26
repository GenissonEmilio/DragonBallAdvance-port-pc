/* Exercise the actual native runtime SWI entry; no guest code executes. */
#include "gba/gba_runtime.h"
#include "gba/display.h"
#include <stdio.h>
#include <string.h>
int main(int n, char **v) {
  if (n != 4) return 2;
  char *args[] = {v[0], v[1], "--headless"};
  display_parse_args(3, args);
  gba_init(v[1]);
  FILE *input = fopen(v[2], "rb"), *output = fopen(v[3], "wb");
  if (!input || !output) return 1;
  uint32_t row[5];
  unsigned count = 0;
  while (fread(row, sizeof(row), 1, input) == 1) {
    memcpy(r, row+1, 4*sizeof(uint32_t));
    gba_swi(row[0]);
    if (fwrite(r, 4*sizeof(uint32_t), 1, output) != 1) return 1;
    ++count;
  }
  int ok = !ferror(input) && feof(input);
  ok &= !fclose(input); ok &= !fclose(output);
  gba_shutdown();
  printf("%u actual runtime SWI math cases\n", count);
  return ok ? 0 : 1;
}
