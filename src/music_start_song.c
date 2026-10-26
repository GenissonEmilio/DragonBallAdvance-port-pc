#include "audio.h"
/* USA 0x0810ADB8: 44 complete bytes match the ROM. */
void Music_StartSong(DbaaU16 song) {
  register const struct MusicPlayerEntry *players __asm__("r2") =
      gMusicPlayerTable;
  const struct DbaaSongEntry *songs = gSongTable;
  const struct DbaaSongEntry *entry = songs + song;
  const struct MusicPlayerEntry *player =
      (const struct MusicPlayerEntry *)((DbaaU32)entry->player * 12 +
                                        (DbaaU32)players);
  MusicPlayer_Start(player->player, entry->header);
}
