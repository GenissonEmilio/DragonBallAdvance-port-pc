/* Portable C counterpart of USA BDVE 0x0810A724. Its behavior is validated
 * separately; asm/music_player_update.s owns exact GBA byte reproduction. */
#include "audio_helpers.h"
#include "music_player.h"

#define R8(a) host->read(host->user, (a), 1)
#define R16(a) host->read(host->user, (a), 2)
#define R32(a) host->read(host->user, (a), 4)
#define W8(a, v) host->write(host->user, (a), (v), 1)
#define W16(a, v) host->write(host->user, (a), (v), 2)
#define W32(a, v) host->write(host->user, (a), (v), 4)
#define CALL(target, a, b, c) Dbaa_AudioCall(host, (target), (a), (b), (c))

static int32_t signed_byte(uint32_t value) {
  value &= 255;
  return value < 128 ? (int32_t)value : (int32_t)value - 256;
}

static void channel_volume(const DbaaMusicHost *host, uint32_t channel,
                           uint32_t track) {
  uint32_t velocity = R8(channel + 0x12);
  int32_t pan = signed_byte(R8(channel + 0x14));
  uint32_t right = ((uint32_t)(128 + pan) * velocity * R8(track + 0x10)) >> 14;
  W8(channel + 2, right > 255 ? 255 : right);
  uint32_t left = ((uint32_t)(127 - pan) * velocity * R8(track + 0x11)) >> 14;
  W8(channel + 3, left > 255 ? 255 : left);
}

void Dbaa_MusicPlayerUpdate(const DbaaMusicHost *host, uint32_t player) {
  uint32_t sound, track, ticks, target, channel;
  int32_t count;
  if (R32(player + 0x34) != 0x68736D53)
    return;
  W32(player + 0x34, 0x68736D54);
  target = R32(player + 0x38);
  if (target)
    CALL(target, R32(player + 0x3C), 0, 0);
  if (R32(player + 4) & 0x80000000u)
    goto unlock;
  sound = R32(0x03007FF0);
  CALL(0x0810B610, player, 0, 0);
  if (R32(player + 4) & 0x80000000u)
    goto unlock;
  ticks = R16(player + 0x22) + R16(player + 0x20);
tempo:
  W16(player + 0x22, ticks);
  if (ticks >= 150) {
    uint32_t bit = 1, active = 0;
    count = (int32_t)R8(player + 8);
    track = R32(player + 0x2C);
    /* Entry precedes the count check, including a zero track count. */
    do {
      if (R8(track) & 0x80) {
        active |= bit;
        channel = R32(track + 0x20);
        while (channel) {
          uint32_t status = R8(channel);
          if (status & 0xC7) {
            uint32_t gate = R8(channel + 0x10);
            if (gate) {
              W8(channel + 0x10, --gate);
              if (!gate)
                W8(channel, status | 0x40);
            }
          } else {
            CALL(0x0810B10C, channel, 0, 0);
          }
          channel = R32(channel + 0x34);
        }
        if (R8(track) & 0x40) {
          CALL(0x0810B120, track, 0, 0);
          W8(track, 0x80);
          W8(track + 0x0F, 2);
          W8(track + 0x13, 64);
          W8(track + 0x19, 22);
          W8(track + 0x24, 1);
        }
        uint32_t wait = R8(track + 1);
        while (!wait) {
          uint32_t command = R32(track + 0x40);
          uint32_t opcode = R8(command);
          if (opcode < 0x80) {
            opcode = R8(track + 7);
          } else {
            W32(track + 0x40, command + 1);
            if (opcode >= 0xBD)
              W8(track + 7, opcode);
          }
          if (opcode >= 0xCF) {
            CALL(R32(sound + 0x38), opcode - 0xCF, player, track);
          } else if (opcode > 0xB0) {
            uint32_t index = opcode - 0xB1;
            W8(player + 0x0A, index);
            CALL(R32(R32(sound + 0x34) + index * 4), player, track, 0);
            if (!R8(track))
              goto track_finished;
          } else {
            W8(track + 1, R8(0x08A676D4 + opcode - 0x80));
          }
          wait = R8(track + 1);
        }
        W8(track + 1, wait - 1);
        uint32_t speed = R8(track + 0x19);
        if (speed && R8(track + 0x17)) {
          uint32_t delay = R8(track + 0x1C);
          if (delay) {
            W8(track + 0x1C, delay - 1);
          } else {
            uint32_t phase = R8(track + 0x1A) + speed;
            int32_t triangle, product, modulation;
            W8(track + 0x1A, phase);
            triangle = ((phase - 64u) & 0x80) ? signed_byte(phase)
                                              : 128 - (int32_t)phase;
            product = triangle * (int32_t)R8(track + 0x17);
            /* Arithmetic shift by six, without a host signed-shift assumption.
             */
            modulation = product >= 0 ? product / 64 : -((-product + 63) / 64);
            if ((R8(track + 0x16) ^ (uint32_t)modulation) & 255) {
              W8(track + 0x16, (uint32_t)modulation);
              W8(track, R8(track) | (R8(track + 0x18) ? 3 : 12));
            }
          }
        }
      }
    track_finished:
      if (--count <= 0)
        break;
      track += 80;
      bit <<= 1;
    } while (1);
    W32(player + 12, R32(player + 12) + 1);
    if (!active) {
      W32(player + 4, 0x80000000u);
      goto unlock;
    }
    W32(player + 4, active);
    ticks = R16(player + 0x22) - 150u;
    goto tempo;
  }
  count = (int32_t)R8(player + 8);
  track = R32(player + 0x2C);
  do {
    uint32_t status = R8(track);
    if ((status & 0x80) && (status & 15)) {
      CALL(0x0810B6D8, player, track, 0);
      channel = R32(track + 0x20);
      while (channel) {
        if (!(R8(channel) & 0xC7)) {
          CALL(0x0810B10C, channel, 0, 0);
        } else {
          uint32_t type = R8(channel + 1) & 7;
          if (R8(track) & 3) {
            channel_volume(host, channel, track);
            if (type)
              W8(channel + 0x1D, R8(channel + 0x1D) | 1);
          }
          if (R8(track) & 12) {
            int32_t key = (int32_t)R8(channel + 8) + signed_byte(R8(track + 8));
            uint32_t frequency;
            if (key < 0)
              key = 0;
            if (type) {
              uint32_t callback = R32(sound + 0x30);
              uint32_t fine = R8(track + 9);
              frequency = CALL(callback, type, (uint32_t)key, fine);
              W32(channel + 0x20, frequency);
              W8(channel + 0x1D, R8(channel + 0x1D) | 2);
            } else {
              frequency = CALL(0x0810AC90, R32(channel + 0x24), (uint32_t)key,
                               R8(track + 9));
              W32(channel + 0x20, frequency);
            }
          }
        }
        channel = R32(channel + 0x34);
      }
      W8(track, R8(track) & 0xF0);
    }
    if (--count <= 0)
      break;
    {
      uint32_t old = track;
      track += 80;
      /* Original BGT uses NZV from ADD, including signed overflow. */
      if (old >= 0x80000000u && old <= 0xFFFFFFB0u)
        break;
    }
  } while (1);
unlock:
  W32(player + 0x34, 0x68736D53);
}
