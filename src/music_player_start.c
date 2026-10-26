/* USA 0x0810B4EC: 228 complete bytes match the ROM. */
#include "audio.h"
#include "services.h"
/* Empty GNU C constraints retain allocation and original value lifetimes. */
#define IN_REGISTER(reg, expression)                                           \
  ({                                                                           \
    register DbaaU32 dbaaRegisterValue __asm__(reg) = (DbaaU32)(expression);   \
    __asm__("" : "+r"(dbaaRegisterValue));                                     \
    dbaaRegisterValue;                                                         \
  })
void MusicPlayer_Start(struct MusicPlayer *object, const void *header) {
  struct MusicPlayer *player = (struct MusicPlayer *)IN_REGISTER("r5", object);
  const struct DbaaSongHeader *song = header;
  int i, limit;
  DbaaU32 zero;
  struct MusicTrack *track;
  DbaaU32 priority;
  DbaaU32 check;
  int status;
  if (player->lock != 0x68736D53)
    return;
  check = ({
    register DbaaU32 value __asm__("r0") = player->priority;
    __asm__("" : "+r"(value));
    value;
  });
  priority = song->priority;
  if (check && ((player->song && ({
                   register struct MusicTrack *first __asm__("r1") =
                       player->tracks;
                   register DbaaU32 mask __asm__("r0");
                   __asm__("" : "+r"(first));
                   mask = 0x40;
                   __asm__("" : "+r"(mask));
                   mask &= first->status;
                   __asm__("" : "+r"(mask));
                   mask;
                 })) ||
                ((status = IN_REGISTER("r1", player->status),
                  (DbaaU16)player->status && status >= 0)))) {
    priority = *(volatile const DbaaU8 *)&song->priority;
    if (player->songPriority > priority)
      return;
  }
  player->lock++;
  player->status = 0;
  player->song = song;
  player->voicegroup = song->voicegroup;
  player->songPriority = priority;
  player->clock = 0;
  player->tempo = 150;
  player->tempoInterval = 150;
  player->tempoScale = 256;
  player->tempoCounter = 0;
  player->fadeInterval = 0;
  i = 0;
  track = (struct MusicTrack *)IN_REGISTER("r4", player->tracks);
  /* Reserve a scratch register across the first track-count load. */
  {
    register DbaaU32 scratch __asm__("r0");
    __asm__("" : "=r"(scratch));
    limit = song->trackCount;
    __asm__("" : : "r"(scratch));
  }
  /* Explicit C blocks preserve the two entry/exit paths of the track loop. */
  if (i >= limit)
    goto remaining_tracks;
  if (i >= player->trackCount)
    goto apply_mode;
  i = IN_REGISTER("r6", i);
  zero = IN_REGISTER("r8", i);
start_track:
  {
    MusicTrack_Stop(player, track);
    {
      register DbaaU32 held __asm__("r0") = 0xC0;
      __asm__("" : : "r"(held));
      track->status = held;
      track->channel = (struct SoundChannel *)zero;
      __asm__("" : : "r"(held));
    }
    {
      register DbaaU32 offset __asm__("r1") = i * 4;
      register const DbaaU8 *base __asm__("r0");
      __asm__("" : "+r"(offset));
      base = (const DbaaU8 *)IN_REGISTER("r0", song);
      base += 8;
      __asm__("" : "+r"(base));
      track->command = *(const DbaaU8 *const *)(base + offset);
    }
    i++;
    track++;
    limit = song->trackCount;
    if (i >= limit)
      goto remaining_tracks;
    if (i < player->trackCount)
      goto start_track;
  }
remaining_tracks:
  while (i < player->trackCount) {
    MusicTrack_Stop(player, track);
    track->status = 0;
    i++;
    track++;
  }
apply_mode:
  {
    register DbaaU32 mode __asm__("r0") = 0x80;
    __asm__("" : "+r"(mode));
    mode &= song->mode;
    __asm__("" : "+r"(mode));
    if (mode)
      Func_0810B2D0(*(const volatile DbaaU8 *)&song->mode);
  }
  player->lock = 0x68736D53;
}
