#include "save_storage.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  size_t size = (size_t)strtoul(argv[2], NULL, 10);
  unsigned count = (unsigned)strtoul(argv[3], NULL, 10);
  unsigned char *data = malloc(size ? size : 1);
  if (!data)
    return 1;
  uint32_t error = 0;
  for (unsigned i = 0; i < count && !error; ++i) {
    for (size_t j = 0; j < size; ++j)
      data[j] = (unsigned char)((j * 73 + (i & 1 ? 0x5A : 0xA5)) & 255);
    error = Dbaa_SaveWriteAtomic(argv[1], data, size);
  }
  free(data);
  printf("{\"ok\":%s,\"error\":%u,\"size\":%zu,\"count\":%u}\n",
         error ? "false" : "true", error, size, count);
  return error ? 1 : 0;
}
