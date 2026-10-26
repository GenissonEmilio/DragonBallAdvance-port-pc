/* Replace only after a complete, flushed sibling file has been closed. */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include "save_storage.h"
#include <stdio.h>
#include <windows.h>

uint32_t Dbaa_SaveWriteAtomic(const char *path, const void *bytes, size_t size) {
  if (!path || !*path || !bytes || !size || size > UINT32_MAX)
    return ERROR_INVALID_PARAMETER;
  static LONG sequence;
  char temporary[1024];
  int count = snprintf(temporary, sizeof(temporary), "%s.tmp.%lu.%llu.%ld", path,
                       (unsigned long)GetCurrentProcessId(),
                       (unsigned long long)GetTickCount64(),
                       (long)InterlockedIncrement(&sequence));
  if (count < 0 || (size_t)count >= sizeof(temporary))
    return ERROR_FILENAME_EXCED_RANGE;
  HANDLE file = CreateFileA(temporary, GENERIC_WRITE, 0, NULL, CREATE_NEW,
                             FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, NULL);
  if (file == INVALID_HANDLE_VALUE)
    return GetLastError();
  DWORD written = 0;
  uint32_t error = 0;
  if (!WriteFile(file, bytes, (DWORD)size, &written, NULL))
    error = GetLastError();
  else if (written != size)
    error = ERROR_WRITE_FAULT;
  if (!error && !FlushFileBuffers(file))
    error = GetLastError();
  if (!CloseHandle(file) && !error)
    error = GetLastError();
  if (!error && !MoveFileExA(temporary, path,
                             MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
    error = GetLastError();
  if (error)
    DeleteFileA(temporary); /* This unique sibling is the only cleanup target. */
  return error;
}
