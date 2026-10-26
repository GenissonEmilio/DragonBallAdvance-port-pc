/* USA 0x0810BFAC: 344 complete linked bytes match; C/GNU C only. */
#include "audio.h"
extern void (*gSoundCommands[])(struct MusicPlayer *, struct MusicTrack *);
#define MEMACC_COND_JUMP(cond)                                                 \
  if (cond)                                                                    \
    goto cond_true;                                                            \
  else                                                                         \
    goto cond_false;
void MusicEvent_MemoryAccess(struct MusicPlayer *playerInput,
                             struct MusicTrack *trackInput) {
  register struct MusicPlayer *mplayInfo __asm__("r4") = playerInput;
  register struct MusicTrack *track __asm__("r6") = trackInput;
  DbaaU32 op;
  register DbaaU8 *addr __asm__("r3");
  register DbaaU32 data __asm__("r2");
  register const DbaaU8 *command __asm__("r1") = track->command;
  register const DbaaU8 *next __asm__("r2");
  register DbaaU8 *base __asm__("r0");
  register DbaaU32 index __asm__("r1");
  register const DbaaU8 *after __asm__("r0");
  __asm__("" : "+r"(mplayInfo), "+r"(track));
  __asm__("" : "+r"(command));
  op = *command;
  next = command + 1;
  __asm__("" : "+r"(next));
  track->command = next;
  base = mplayInfo->memory;
  __asm__("" : "+r"(base));
  index = command[1];
  __asm__("" : "+r"(index));
  addr = (DbaaU8 *)(index + (DbaaU32)base);
  __asm__("" : "+r"(addr));
  after = next + 1;
  __asm__("" : "+r"(after));
  track->command = after;
  data = next[1];
  __asm__("" : "+r"(data));
  after++;
  track->command = after;

  switch (op) {
  case 0:
    *addr = data;
    return;
  case 1: {
    register DbaaU32 left __asm__("r1") = *addr, result __asm__("r0");
    __asm__("" : "+r"(left));
    result = left + data;
    __asm__("" : "+r"(result));
    *addr = result;
    return;
  }
  case 2: {
    register DbaaU32 left __asm__("r1") = *addr, result __asm__("r0");
    __asm__("" : "+r"(left));
    result = left - data;
    __asm__("" : "+r"(result));
    *addr = result;
    return;
  }
  case 3:
    *addr = ((DbaaU8 *)mplayInfo->memory)[data];
    return;
  case 4: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r1"), result __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    result = left + *source;
    __asm__("" : "+r"(result));
    *addr = result;
    return;
  }
  case 5: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r1"), result __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    result = left - *source;
    __asm__("" : "+r"(result));
    *addr = result;
    return;
  }
  case 6: {
    register DbaaU32 left __asm__("r3") = *addr;
    __asm__("" : "+r"(left));
    MEMACC_COND_JUMP(left == data)
  }
  case 7: {
    register DbaaU32 left __asm__("r3") = *addr;
    __asm__("" : "+r"(left));
    MEMACC_COND_JUMP(left != data)
  }
  case 8: {
    register DbaaU32 left __asm__("r3") = *addr;
    __asm__("" : "+r"(left));
    MEMACC_COND_JUMP(left > data)
  }
  case 9: {
    register DbaaU32 left __asm__("r3") = *addr;
    __asm__("" : "+r"(left));
    MEMACC_COND_JUMP(left >= data)
  }
  case 10: {
    register DbaaU32 left __asm__("r3") = *addr;
    __asm__("" : "+r"(left));
    MEMACC_COND_JUMP(left <= data)
  }
  case 11: {
    register DbaaU32 left __asm__("r3") = *addr;
    __asm__("" : "+r"(left));
    MEMACC_COND_JUMP(left < data)
  }
  case 12: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r3"), right __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    right = *source;
    __asm__("" : "+r"(right));
    MEMACC_COND_JUMP(left == right)
  }
  case 13: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r3"), right __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    right = *source;
    __asm__("" : "+r"(right));
    MEMACC_COND_JUMP(left != right)
  }
  case 14: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r3"), right __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    right = *source;
    __asm__("" : "+r"(right));
    MEMACC_COND_JUMP(left > right)
  }
  case 15: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r3"), right __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    right = *source;
    __asm__("" : "+r"(right));
    MEMACC_COND_JUMP(left >= right)
  }
  case 16: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r3"), right __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    right = *source;
    __asm__("" : "+r"(right));
    MEMACC_COND_JUMP(left <= right)
  }
  case 17: {
    register DbaaU8 *source __asm__("r0") =
        ((DbaaU8 *)mplayInfo->memory) + data;
    register DbaaU32 left __asm__("r3"), right __asm__("r0");
    __asm__("" : "+r"(source));
    left = *addr;
    __asm__("" : "+r"(left));
    right = *source;
    __asm__("" : "+r"(right));
    MEMACC_COND_JUMP(left < right)
  }
  default:
    return;
  }

cond_true:
  {
    {
      void (*func)(struct MusicPlayer *, struct MusicTrack *) =
          *(&gSoundCommands[1]);
      func(mplayInfo, track);
    }
    return;
  }

cond_false:
  track->command += 4;
}
