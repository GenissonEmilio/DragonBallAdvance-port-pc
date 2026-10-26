#ifndef DBAA_SAVE_STORAGE_H
#define DBAA_SAVE_STORAGE_H
#include <stddef.h>
#include <stdint.h>
/* Uses the same Windows ANSI path encoding as the current runtime's fopen.
 * Returns zero on success, otherwise the Windows error code. */
uint32_t Dbaa_SaveWriteAtomic(const char *path, const void *bytes, size_t size);
#endif
