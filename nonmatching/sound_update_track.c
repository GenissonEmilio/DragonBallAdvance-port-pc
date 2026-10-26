/* NONMATCHING ARM C candidate for USA 0x0810AA00.
 * Native production C is in port/audio/audio_helpers.c; exact GBA bytes are
 * separately reconstructed in asm/sound_update_track.s. */
#include "audio.h"
extern const DbaaU8 gMusicWaitTable[];
void Sound_ClearChannelChain(struct SoundChannel *);
DbaaU32 Music_CalculateFrequency(const void *, DbaaU8, DbaaU8);
#define R8(a) (*(DbaaU8 *)(a))
#define R16(a) (*(DbaaU16 *)(a))
#define R32(a) (*(DbaaU32 *)(a))
#define W8(a, v) (*(DbaaU8 *)(a) = (v))
#define W16(a, v) (*(DbaaU16 *)(a) = (v))
#define W32(a, v) (*(DbaaU32 *)(a) = (v))
#define s8(a) ((int)(DbaaS8)(a))
#define CALL(t, a, b, c)                                                       \
  (((DbaaU32 (*)(DbaaU32, DbaaU32, DbaaU32))(t))((a), (b), (c)))
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

void Sound_UpdateTrack(DbaaU32 duration, DbaaU32 player, DbaaU32 track) {
  DbaaU32 sound, command, value, tone, type, key, index, priority, cgb, channel,
      chosen, best_priority, best_track, releasing, status, current_priority,
      owner, old_head, wave, frequency, sweep;
  int rhythm_pan, count, pitch_key;

  sound = (DbaaU32)gSoundInfoPointer;
  W8(track + 4, R8((DbaaU32)gMusicWaitTable + duration));
  command = R32(track + 0x40), value = R8(command);
  if (value < 0x80) {
    W8(track + 5, value);
    value = R8(++command);
    if (value < 0x80) {
      W8(track + 6, value);
      value = R8(++command);
      if (value < 0x80) {
        W8(track + 4, R8(track + 4) + value);
        ++command;
      }
    }
    W32(track + 0x40, command);
  }
  rhythm_pan = 0;
  tone = track + 0x24, type = R8(tone);
  if (type & 0xC0) {
    key = R8(track + 5);
    index = (type & 0x40) ? R8(R32(track + 0x2C) + key) : key;
    tone = R32(track + 0x28) + 12 * index;
    if (R8(tone) & 0xC0)
      return;
    if (type & 0x80) {
      value = R8(tone + 3);
      if (value & 0x80)
        rhythm_pan = ((int)value - 0xC0) * 2;
      key = R8(tone + 1);
    }
  } else {
    key = R8(track + 5);
  }
  priority = R8(track + 0x1D) + R8(player + 9);
  if (priority > 255)
    priority = 255;
  cgb = R8(tone) & 7;
  if (cgb) {
    channel = R32(sound + 0x1C);
    if (!channel)
      return;
    channel += (cgb - 1) * 64;
    status = R8(channel);
    if ((status & 0xC7) && !(status & 0x40)) {
      current_priority = R8(channel + 0x13);
      if (current_priority > priority ||
          (current_priority == priority && R32(channel + 0x2C) < track))
        return;
    }
  } else {
    chosen = 0, best_priority = priority, best_track = track;
    releasing = 0;
    count = (int)R8(sound + 6);
    channel = sound + 0x50;
    /* Like the original, inspect the first channel even when count is zero. */
    do {
      status = R8(channel);
      if (!(status & 0xC7))
        goto selected;
      if (status & 0x40) {
        if (!releasing) {
          releasing = 1;
          best_priority = R8(channel + 0x13);
          best_track = R32(channel + 0x2C);
          chosen = channel;
          goto next_channel;
        }
      } else if (releasing) {
        goto next_channel;
      }
      current_priority = R8(channel + 0x13);
      if (current_priority < best_priority) {
        best_priority = current_priority;
        best_track = R32(channel + 0x2C);
        chosen = channel;
      } else if (current_priority == best_priority) {
        owner = R32(channel + 0x2C);
        if (owner >= best_track) {
          best_track = owner;
          chosen = channel;
        }
      }
    next_channel:
      channel += 64;
    } while (--count > 0);
    channel = chosen;
    if (!channel)
      return;
  }
selected:
  Sound_ClearChannelChain((struct SoundChannel *)channel);
  W32(channel + 0x30, 0);
  old_head = R32(track + 0x20);
  W32(channel + 0x34, old_head);
  if (old_head)
    W32(old_head + 0x30, channel);
  W32(track + 0x20, channel);
  W32(channel + 0x2C, track);
  value = R8(track + 0x1B);
  W8(track + 0x1C, value);
  if (value)
    Music_ClearModulation((void *)player, (void *)track);
  MusicTrack_UpdateVolumePitch((struct MusicPlayer *)player,
                               (struct MusicTrack *)track);
  W32(channel + 0x10, R32(track + 4));
  W8(channel + 0x13, priority);
  W8(channel + 8, key);
  W8(channel + 0x14, (DbaaU32)rhythm_pan);
  W8(channel + 1, R8(tone));
  wave = R32(tone + 4);
  W32(channel + 0x24, wave);
  W32(channel + 4, R32(tone + 8));
  W16(channel + 0xC, R16(track + 0x1E));
  UpdateChannelVolume((DbaaU8 *)channel, (DbaaU8 *)track);
  pitch_key = (int)R8(channel + 8) + s8(R8(track + 8));
  if (pitch_key < 0)
    pitch_key = 0;

  if (cgb) {
    W8(channel + 0x1E, R8(tone + 2));
    sweep = R8(tone + 3);
    if ((sweep & 0x80) || !(sweep & 0x70))
      sweep = 8;
    W8(channel + 0x1F, sweep);
    frequency = CALL(R32(sound + 0x30), cgb, (DbaaU32)pitch_key, R8(track + 9));
  } else {
    frequency = Music_CalculateFrequency((void *)wave, (DbaaU32)pitch_key,
                                         R8(track + 9));
  }
  W32(channel + 0x20, frequency);
  W8(channel, 0x80);
  W8(track, R8(track) & 0xF0);
  return;
}
