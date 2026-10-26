/* Semantic reconstruction of USA 0810A724..0810A98C.
 * NONMATCHING: the original entry/epilogue and channel-volume helper use a
 * custom assembly calling convention. This file is not a production target.
 */
#include "audio.h"
extern const DbaaU8 gMusicWaitTable[];
void Music_FadeOutBody(struct MusicPlayer *);
void MusicTrack_UpdateVolumePitch(struct MusicPlayer *, struct MusicTrack *);
void Sound_ClearChannelChain(struct SoundChannel *);
DbaaU32 Music_CalculateFrequency(const void *, DbaaU8, DbaaU8);

/* Reconstructs the arithmetic of the r4/r5 helper at 0810A9D0. Inlining
 * removes the nonstandard call requirement; it is not a matching claim. */
static __inline__ void UpdateChannelVolume(DbaaU8 *channel, DbaaU8 *track) {
  int velocity = channel[0x12];
  int pan = (DbaaS8)channel[0x14];
  DbaaU32 right = ((128 + pan) * velocity * track[0x10]) >> 14;
  DbaaU32 left = ((127 - pan) * velocity * track[0x11]) >> 14;
  if (right > 255)
    right = 255;
  if (left > 255)
    left = 255;
  channel[2] = right;
  channel[3] = left;
}

void MusicPlayer_Update(struct MusicPlayer *player) {
  struct SoundInfo *sound;
  DbaaU8 *track;
  int count;
  DbaaU32 ticks;
  if (player->lock != 0x68736D53)
    return;
  player->lock++;
  if (player->nextPlayerMain)
    player->nextPlayerMain(player->nextPlayer);
  if ((int)player->status < 0)
    goto unlock;
  sound = gSoundInfoPointer;
  Music_FadeOutBody(player);
  if ((int)player->status < 0)
    goto unlock;
  ticks = player->tempoCounter + player->tempoInterval;
goto_tempo:
  player->tempoCounter = ticks;
  if (ticks >= 150) {
    DbaaU32 bit = 1, active = 0;
    count = player->trackCount;
    track = (void *)player->tracks;
    /* The ROM enters the first record before testing the count. */
    do {
      if (track[0] & 0x80) {
        struct SoundChannel *channel;
        active |= bit;
        channel = *(struct SoundChannel **)(track + 0x20);
        while (channel) {
          DbaaU8 *raw = (void *)channel;
          if (channel->status & 0xC7) {
            if (raw[0x10]) {
              raw[0x10]--;
              if (!raw[0x10])
                channel->status |= 0x40;
            }
          } else
            Sound_ClearChannelChain(channel);
          channel = channel->next;
        }
        if (track[0] & 0x40) {
          MusicPlayer_Clear((void *)track);
          track[0] = 0x80;
          track[0xF] = 2;
          track[0x13] = 64;
          track[0x19] = 22;
          track[0x24] = 1;
        }
        while (!track[1]) {
          const DbaaU8 *command = *(const DbaaU8 **)(track + 0x40);
          DbaaU32 opcode = *command;
          if (opcode < 0x80)
            opcode = track[7];
          else {
            *(const DbaaU8 **)(track + 0x40) = command + 1;
            if (opcode >= 0xBD)
              track[7] = opcode;
          }
          if (opcode >= 0xCF) {
            ((void (*)(DbaaU32, struct MusicPlayer *,
                       DbaaU8 *))sound->callback38)(opcode - 0xCF, player,
                                                    track);
          } else if (opcode > 0xB0) {
            DbaaU32 index = opcode - 0xB1;
            ((DbaaU8 *)player)[0xA] = index;
            ((void (*)(struct MusicPlayer *, DbaaU8 *))sound->commands[index])(
                player, track);
            if (!track[0])
              goto track_finished;
          } else {
            track[1] =
                *(const DbaaU8 *)((DbaaU32)gMusicWaitTable + opcode - 0x80);
          }
        }
        track[1]--;
        if (track[0x19] && track[0x17]) {
          if (track[0x1C])
            track[0x1C]--;
          else {
            DbaaU32 phase = track[0x1A] + track[0x19];
            int triangle, modulation;
            track[0x1A] = phase;
            if ((int)((phase - 64) << 24) < 0)
              triangle = (DbaaS8)phase;
            else
              triangle = 128 - (int)phase;
            modulation = (triangle * track[0x17]) >> 6;
            if ((DbaaU8)(track[0x16] ^ modulation)) {
              track[0x16] = modulation;
              track[0] |= track[0x18] ? 3 : 12;
            }
          }
        }
      }
    track_finished:
      count--;
      if (count <= 0)
        break;
      track += 0x50;
      bit <<= 1;
    } while (1);
    player->clock++;
    if (!active) {
      player->status = 0x80000000;
      goto unlock;
    }
    player->status = active;
    /* Preserve the 32-bit subtraction before the 16-bit store and comparison.
     */
    ticks = (DbaaU32)player->tempoCounter - 150;
    goto goto_tempo;
  }
  count = player->trackCount;
  track = (void *)player->tracks;
  do {
    if ((track[0] & 0x80) && (track[0] & 15)) {
      struct SoundChannel *channel;
      MusicTrack_UpdateVolumePitch(player, (void *)track);
      channel = *(struct SoundChannel **)(track + 0x20);
      while (channel) {
        DbaaU8 *raw = (void *)channel;
        if (!(channel->status & 0xC7))
          Sound_ClearChannelChain(channel);
        else {
          DbaaU32 type = channel->type & 7;
          if (track[0] & 3) {
            UpdateChannelVolume(raw, track);
            if (type)
              raw[0x1D] |= 1;
          }
          if (track[0] & 12) {
            int key = raw[8] + (DbaaS8)track[8];
            if (key < 0)
              key = 0;
            if (type) {
              *(DbaaU32 *)(raw + 0x20) =
                  ((int (*)(DbaaU8, DbaaU8, DbaaU8))sound->callback30)(
                      type, key, track[9]);
              raw[0x1D] |= 2;
            } else {
              *(DbaaU32 *)(raw + 0x20) = Music_CalculateFrequency(
                  *(const void **)(raw + 0x24), key, track[9]);
            }
          }
        }
        channel = channel->next;
      }
      track[0] &= 0xF0;
    }
    count--;
    if (count <= 0)
      break;
    track = (DbaaU8 *)((DbaaU32)track + 0x50);
    /* The ROM's final BGT tests the pointer addition's flags. */
    if ((int)(DbaaU32)track <= 0)
      break;
  } while (1);
unlock:
  player->lock = 0x68736D53;
}
