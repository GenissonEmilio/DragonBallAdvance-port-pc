/* Native counterparts of the matched audio services. Address resolution is
 * explicit so game pointers stay 32-bit on a 64-bit host. No ARM execution. */
#include "audio_helpers.h"

#define R8(a) host->read(host->user, (a), 1)
#define R16(a) host->read(host->user, (a), 2)
#define R32(a) host->read(host->user, (a), 4)
#define W8(a, v) host->write(host->user, (a), (v), 1)
#define W16(a, v) host->write(host->user, (a), (v), 2)
#define W32(a, v) host->write(host->user, (a), (v), 4)
#define CALL(t, a, b, c) Dbaa_AudioCall(host, (t), (a), (b), (c))

static int32_t s8(uint32_t v) {
  return (v & 255) < 128 ? (int32_t)(v & 255) : (int32_t)(v & 255) - 256;
}
static int32_t s16(uint32_t v) {
  return (v & 65535) < 32768 ? (int32_t)(v & 65535)
                             : (int32_t)(v & 65535) - 65536;
}
static int32_t floor256(int32_t v) {
  return v >= 0 ? v / 256 : -((-v + 255) / 256);
}

uint32_t Dbaa_AudioClear64(const DbaaMusicHost *host, uint32_t destination) {
  for (uint32_t offset = 0; offset < 64; offset += 4)
    W32(destination + offset, 0);
  return destination + 64;
}

uint32_t Dbaa_AudioUnlinkChannel(const DbaaMusicHost *host, uint32_t channel) {
  uint32_t track = R32(channel + 0x2C);
  if (track) {
    uint32_t next = R32(channel + 0x34), previous = R32(channel + 0x30);
    if (previous)
      W32(previous + 0x34, next);
    else
      W32(track + 0x20, next);
    if (next)
      W32(next + 0x30, previous);
    W32(channel + 0x2C, 0);
  }
  return channel;
}

uint32_t Dbaa_AudioFilterAddress(const DbaaMusicHost *host, uint32_t source,
                                 uint32_t value) {
  (void)host;
  if (source >> 25)
    return value;
  if (source < 0x08A67460)
    return 0;
  return (source >> 14) ? 0 : value;
}

uint32_t Dbaa_AudioReadByte(const DbaaMusicHost *host, uint32_t source) {
  /* The original reads before rejecting the address. Preserve that order. */
  uint32_t value = R8(source);
  return Dbaa_AudioFilterAddress(host, source, value);
}

uint32_t Dbaa_SoundCopyCommandTable(const DbaaMusicHost *host,
                                    uint32_t destination) {
  uint32_t source = 0x08A67460;
  for (uint32_t remaining = 36; remaining; --remaining) {
    uint32_t value = R32(source);
    value = Dbaa_AudioFilterAddress(host, source, value);
    W32(destination, value);
    destination += 4;
    source += 4;
  }
  return destination;
}

uint32_t Dbaa_MusicEventFine(const DbaaMusicHost *host, uint32_t player,
                             uint32_t track) {
  uint32_t channel = R32(track + 0x20);
  (void)player;
  while (channel) {
    uint32_t status = R8(channel);
    if (status & 0xC7)
      W8(channel, status | 0x40);
    Dbaa_AudioUnlinkChannel(host, channel);
    channel = R32(channel + 0x34);
  }
  W8(track, 0);
  return 0;
}

uint32_t Dbaa_MusicTrackStop(const DbaaMusicHost *host, uint32_t player,
                             uint32_t track) {
  (void)player;
  if (R8(track) & 0x80) {
    uint32_t channel = R32(track + 0x20);
    while (channel) {
      if (R8(channel)) {
        uint32_t type = R8(channel + 1) & 7;
        if (type)
          CALL(R32(R32(0x03007FF0) + 0x2C), type, 0, 0);
        W8(channel, 0);
      }
      W32(channel + 0x2C, 0);
      channel = R32(channel + 0x34);
    }
    W32(track + 0x20, 0);
  }
  return 0;
}

uint32_t Dbaa_MusicFadeOutBody(const DbaaMusicHost *host, uint32_t player) {
  uint32_t interval = R16(player + 0x24), level, track, count;
  if (!interval)
    return 0;
  uint32_t counter = (R16(player + 0x26) - 1u) & 65535;
  W16(player + 0x26, counter);
  if (counter)
    return 0;
  W16(player + 0x26, interval);
  level = R16(player + 0x28);
  if (level & 2) {
    level = (level + 16) & 65535;
    W16(player + 0x28, level);
    if (level > 255) {
      level = 256;
      W16(player + 0x28, level);
      W16(player + 0x24, 0);
    }
  } else {
    level = (level - 16u) & 65535;
    W16(player + 0x28, level);
    if (s16(level) <= 0) {
      count = R8(player + 8);
      track = R32(player + 0x2C);
      while (count--) {
        Dbaa_MusicTrackStop(host, player, track);
        /* The ROM reloads the level after each potentially indirect stop. */
        if (!(R16(player + 0x28) & 1))
          W8(track, 0);
        track += 80;
      }
      uint32_t status = (R16(player + 0x28) & 1) ? R32(player + 4) | 0x80000000u
                                                 : 0x80000000u;
      W32(player + 4, status);
      W16(player + 0x24, 0);
      return 0;
    }
  }
  count = R8(player + 8);
  track = R32(player + 0x2C);
  while (count--) {
    uint32_t status = R8(track);
    if (status & 0x80) {
      W8(track + 0x13, R16(player + 0x28) >> 2);
      W8(track, status | 3);
    }
    track += 80;
  }
  return 0;
}

uint32_t Dbaa_MusicTrackVolumePitch(const DbaaMusicHost *host, uint32_t player,
                                    uint32_t track) {
  uint32_t status = R8(track);
  (void)player;
  if (status & 1) {
    uint32_t volume = R8(track + 0x13) * R8(track + 0x12) >> 5;
    uint32_t type = R8(track + 0x18);
    if (type == 1)
      volume = (uint32_t)(s8(R8(track + 0x16)) + 128) * volume >> 7;
    int32_t pan = 2 * s8(R8(track + 0x14)) + s8(R8(track + 0x15));
    if (type == 2)
      pan += s8(R8(track + 0x16));
    if (pan < -128)
      pan = -128;
    if (pan > 127)
      pan = 127;
    W8(track + 0x10, (uint32_t)(pan + 128) * volume >> 8);
    W8(track + 0x11, (uint32_t)(127 - pan) * volume >> 8);
  }
  /* The original reloads status after the volume stores, then reads bend,
   * range and tuning in this order. Keep callbacks sequenced explicitly. */
  status = R8(track);
  if (status & 4) {
    int32_t bend = s8(R8(track + 0x0E));
    uint32_t range = R8(track + 0x0F);
    int32_t pitch = (s8(R8(track + 0x0C)) + bend * (int32_t)range) * 4;
    pitch += s8(R8(track + 0x0A)) * 256;
    pitch += s8(R8(track + 0x0B)) * 256;
    pitch += (int32_t)R8(track + 0x0D);
    if (!R8(track + 0x18))
      pitch += s8(R8(track + 0x16)) * 16;
    W8(track + 8, (uint32_t)floor256(pitch));
    W8(track + 9, (uint32_t)pitch);
  }
  W8(track, status & 0xFA);
  return 0;
}

uint32_t Dbaa_MusicCalculateFrequency(const DbaaMusicHost *host, uint32_t wave,
                                      uint32_t key, uint32_t fine) {
  key &= 255;
  uint32_t fraction = (fine & 255) << 24;
  if (key > 178) {
    key = 178;
    fraction = 255u << 24;
  }
  uint32_t map = R8(0x08A674F0 + key);
  uint32_t first = R32(0x08A675A4 + 4 * (map & 15)) >> (map >> 4);
  map = R8(0x08A674F0 + key + 1);
  uint32_t second = R32(0x08A675A4 + 4 * (map & 15)) >> (map >> 4);
  uint32_t frequency = R32(wave + 4);
  /* Match both UMULL high words, including unsigned subtraction/wrap. */
  uint32_t adjustment = (uint32_t)((uint64_t)(second - first) * fraction >> 32);
  return (uint32_t)((uint64_t)frequency * (first + adjustment) >> 32);
}

static int32_t cgbPeriod(const DbaaMusicHost *host, uint32_t map) {
  int32_t period = s16(R16(0x08A67670 + 2 * (map & 15)));
  int32_t divisor = 1 << (map >> 4);
  /* Arithmetic right shift with defined C99 rounding for negative periods. */
  return period >= 0 ? period / divisor : -((-period + divisor - 1) / divisor);
}

uint32_t Dbaa_CgbCalculateFrequency(const DbaaMusicHost *host, uint32_t channel,
                                    uint32_t key, uint32_t fine) {
  channel &= 255;
  key &= 255;
  fine &= 255;
  if (channel == 4) {
    key = key <= 20 ? 0 : key - 21;
    if (key > 59)
      key = 59;
    return R8(0x08A67688 + key);
  }
  if (key <= 35) {
    key = 0;
    fine = 0;
  } else {
    key -= 36;
    if (key > 130) {
      key = 130;
      fine = 255;
    }
  }
  int32_t first = cgbPeriod(host, R8(0x08A675EC + key));
  int32_t second = cgbPeriod(host, R8(0x08A675EC + key + 1));
  return (uint32_t)(first + floor256((second - first) * (int32_t)fine) + 2048);
}

static uint32_t music_event_set_byte(const DbaaMusicHost *host, uint32_t track,
                                     uint32_t offset) {
  uint32_t command = R32(track + 0x40);
  W8(track + offset, R8(command));
  /* The original code reloads the cursor for the instrument fields. */
  if (offset >= 0x20)
    command = R32(track + 0x40);
  W32(track + 0x40, command + 1);
  return 0;
}

uint32_t Dbaa_MusicEventPattern(const DbaaMusicHost *host, uint32_t player,
                                uint32_t track) {
  uint32_t depth = R8(track + 2);
  if (depth >= 3) {
    CALL(0x0810A4E4, player, track, 0);
    return 0;
  }
  uint32_t command = R32(track + 0x40);
  W32(track + 0x44 + depth * 4, command + 4);
  W8(track + 2, R8(track + 2) + 1);
  CALL(0x0810A554, player, track, 0);
  return 0;
}

uint32_t Dbaa_MusicEventPatternEnd(const DbaaMusicHost *host, uint32_t player,
                                   uint32_t track) {
  (void)player;
  uint32_t depth = R8(track + 2);
  if (depth) {
    --depth;
    W8(track + 2, depth);
    W32(track + 0x40, R32(track + 0x44 + depth * 4));
  }
  return 0;
}

uint32_t Dbaa_MusicReadCommandFiltered(const DbaaMusicHost *host,
                                       uint32_t player, uint32_t track) {
  (void)player;
  uint32_t command = R32(track + 0x40);
  W32(track + 0x40, command + 1);
  return Dbaa_AudioReadByte(host, command);
}

uint32_t Dbaa_MusicEventRepeat(const DbaaMusicHost *host, uint32_t player,
                               uint32_t track) {
  uint32_t command = R32(track + 0x40);
  if (!R8(command)) {
    W32(track + 0x40, command + 1);
    CALL(0x0810A554, player, track, 0);
    return 0;
  }
  /* Compare the full increment, including 256, before the byte wraps. */
  uint32_t repeat = R8(track + 3) + 1;
  W8(track + 3, repeat);
  uint32_t count = CALL(0x0810A548, player, track, 0);
  if (repeat < count) {
    CALL(0x0810A554, player, track, 0);
  } else {
    W8(track + 3, 0);
    W32(track + 0x40, command + 5);
  }
  return 0;
}

uint32_t Dbaa_MusicEventPriority(const DbaaMusicHost *host, uint32_t player,
                                 uint32_t track) {
  uint32_t priority = CALL(0x0810A548, player, track, 0);
  W8(track + 0x1D, priority);
  return 0;
}

uint32_t Dbaa_MusicEventTempo(const DbaaMusicHost *host, uint32_t player,
                              uint32_t track) {
  uint32_t tempo = CALL(0x0810A548, player, track, 0) << 1;
  W16(player + 0x1C, tempo);
  uint32_t scale = R16(player + 0x1E);
  W16(player + 0x20, (tempo * scale) >> 8);
  return 0;
}

uint32_t Dbaa_MusicEventKeyShift(const DbaaMusicHost *host, uint32_t player,
                                 uint32_t track) {
  uint32_t key_shift = CALL(0x0810A548, player, track, 0);
  W8(track + 0x0A, key_shift);
  W8(track, R8(track) | 0x0C);
  return 0;
}

uint32_t Dbaa_MusicEventVoice(const DbaaMusicHost *host, uint32_t player,
                              uint32_t track) {
  uint32_t command = R32(track + 0x40);
  uint32_t instrument = R8(command);
  W32(track + 0x40, command + 1);
  uint32_t source = R32(player + 0x30) + 12 * instrument;
  /* The SDK filters all three words using the record's base address. Keep
   * reads interleaved with stores: source and track may overlap. */
  uint32_t value = R32(source);
  W32(track + 0x24, Dbaa_AudioFilterAddress(host, source, value));
  value = R32(source + 4);
  W32(track + 0x28, Dbaa_AudioFilterAddress(host, source, value));
  value = R32(source + 8);
  W32(track + 0x2C, Dbaa_AudioFilterAddress(host, source, value));
  return 0;
}

uint32_t Dbaa_MusicEventVolume(const DbaaMusicHost *host, uint32_t player,
                               uint32_t track) {
  uint32_t volume = CALL(0x0810A548, player, track, 0);
  W8(track + 0x12, volume);
  W8(track, R8(track) | 0x03);
  return 0;
}

uint32_t Dbaa_MusicEventPan(const DbaaMusicHost *host, uint32_t player,
                            uint32_t track) {
  uint32_t pan = CALL(0x0810A548, player, track, 0) - 0x40u;
  W8(track + 0x14, pan);
  W8(track, R8(track) | 3u);
  return 0;
}

uint32_t Dbaa_MusicEventPitchBend(const DbaaMusicHost *host, uint32_t player,
                                  uint32_t track) {
  uint32_t bend = CALL(0x0810A548, player, track, 0) - 0x40u;
  W8(track + 0x0E, bend);
  W8(track, R8(track) | 12u);
  return 0;
}

uint32_t Dbaa_MusicEventBendRange(const DbaaMusicHost *host, uint32_t player,
                                  uint32_t track) {
  uint32_t range = CALL(0x0810A548, player, track, 0);
  W8(track + 0x0F, range);
  W8(track, R8(track) | 0x0Cu);
  return 0;
}

uint32_t Dbaa_MusicEventLfoDelay(const DbaaMusicHost *host, uint32_t player,
                                 uint32_t track) {
  uint32_t lfo_delay = CALL(0x0810A548, player, track, 0);
  W8(track + 0x1B, lfo_delay);
  return 0;
}

uint32_t Dbaa_MusicEventModType(const DbaaMusicHost *host, uint32_t player,
                                uint32_t track) {
  uint32_t mod_type = CALL(0x0810A548, player, track, 0);
  if (R8(track + 0x18) != mod_type) {
    W8(track + 0x18, mod_type);
    W8(track, R8(track) | 0x0Fu);
  }
  return 0;
}

uint32_t Dbaa_MusicEventTune(const DbaaMusicHost *host, uint32_t player,
                             uint32_t track) {
  uint32_t tune = CALL(0x0810A548, player, track, 0) - 0x40u;
  W8(track + 0x0C, tune);
  W8(track, R8(track) | 0xCu);
  return 0;
}

uint32_t Dbaa_MusicEventPort(const DbaaMusicHost *host, uint32_t player,
                             uint32_t track) {
  (void)player;
  uint32_t port_source = R32(track + 0x40);
  uint32_t port_index = R8(port_source);
  uint32_t port_value_source = port_source + 1;
  W32(track + 0x40, port_value_source + 1);
  uint32_t port_value = Dbaa_AudioReadByte(host, port_value_source);
  W8(0x04000060u + port_index, port_value);
  return 0;
}

uint32_t Dbaa_SoundVSyncOn(const DbaaMusicHost *host) {
  uint32_t sound = R32(0x03007FF0);
  uint32_t lock = R32(sound);
  if (lock != 0x68736D53u) {
    W16(0x040000C6, 0xB600);
    W16(0x040000D2, 0xB600);
    (void)R8(sound + 4);
    W8(sound + 4, 0);
    W32(sound, lock - 10u);
  }
  return 0;
}

uint32_t Dbaa_SoundVSyncOff(const DbaaMusicHost *host) {
  uint32_t sound = R32(0x03007FF0);
  uint32_t lock = R32(sound);
  if (lock - 0x68736D53u > 1u)
    return 0;
  W32(sound, lock + 10u);
  if (R32(0x040000C4) & 0x02000000u)
    W32(0x040000C4, 0x84400004u);
  if (R32(0x040000D0) & 0x02000000u)
    W32(0x040000D0, 0x84400004u);
  W16(0x040000C6, 0x400);
  W16(0x040000D2, 0x400);
  /* CpuSet control 0x05000318: fill 0x318 words with the stack zero.
   * Resolve this fixed operation locally; no BIOS or ARM execution is needed.
   */
  for (uint32_t offset = 0; offset < 0xC60; offset += 4)
    W32(sound + 0x350 + offset, 0);
  return 0;
}

uint32_t Dbaa_SoundMode(const DbaaMusicHost *host, uint32_t mode) {
  uint32_t sound = R32(0x03007FF0);
  uint32_t lock = R32(sound);
  if (lock != 0x68736D53u)
    return 0;
  W32(sound, lock + 1u);
  uint32_t value = mode & 0xFFu;
  if (value)
    W8(sound + 5, value & 0x7Fu);
  value = mode & 0xF00u;
  if (value) {
    W8(sound + 6, value >> 8);
    for (uint32_t channel = 0; channel < 12; ++channel)
      W8(sound + 0x50 + channel * 0x40, 0);
  }
  value = mode & 0xF000u;
  if (value)
    W8(sound + 7, value >> 12);
  value = mode & 0xB00000u;
  if (value) {
    uint32_t bias = R8(0x04000089) & 0x3Fu;
    W8(0x04000089, bias | ((value & 0x300000u) >> 14));
  }
  value = mode & 0xF0000u;
  if (value) {
    CALL(0x0810B3BC, 0, 0, 0);
    CALL(0x0810B22C, value, 0, 0);
  }
  W32(sound, 0x68736D53u);
  return 0;
}

/* The ROM's signed division helper returns zero for a zero divisor. Use wide
 * intermediates to interpret ARM words without signed overflow in host C. */
static uint32_t sound_divide(uint32_t numerator, uint32_t denominator) {
  int64_t n = (int64_t)numerator -
              ((numerator & 0x80000000u) ? INT64_C(0x100000000) : 0);
  int64_t d = (int64_t)denominator -
              ((denominator & 0x80000000u) ? INT64_C(0x100000000) : 0);
  return d ? (uint32_t)(n / d) : 0;
}

uint32_t Dbaa_SoundSetFrequency(const DbaaMusicHost *host, uint32_t mode) {
  uint32_t sound = R32(0x03007FF0);
  uint32_t index = (mode >> 16) & 15u;
  W8(sound + 8, index);
  uint32_t samples = R16(0x08A675D4u + ((index - 1u) << 1));
  W32(sound + 0x10, samples);
  W8(sound + 0x0B, sound_divide(1584u, samples));
  uint32_t rate = sound_divide(597275u * samples + 5000u, 10000u);
  W32(sound + 0x14, rate);
  uint32_t reciprocal = sound_divide(0x01000000u, rate) + 1u;
  W32(sound + 0x18, (reciprocal >> 1) | (reciprocal & 0x80000000u));
  W16(0x04000102, 0);
  W16(0x04000100, 0u - sound_divide(280896u, samples));
  CALL(0x0810B438, 0, 0, 0);
  /* The host clock must advance VCOUNT during polling, including when the
   * call starts at line 159. Preserve the original leave-then-enter order. */
  while (R8(0x04000006) == 159u)
    ;
  while (R8(0x04000006) != 159u)
    ;
  W16(0x04000102, 0x80);
  return 0;
}

uint32_t Dbaa_AudioInitialize(const DbaaMusicHost *host) {
  /* CpuSet 0x04000100: copy 256 words of the original RAM continuation.
   * The native mixer uses C; this data copy still belongs to game RAM state. */
  for (uint32_t offset = 0; offset < 1024; offset += 4)
    W32(0x030008B0u + offset, R32(0x0810A108u + offset));
  CALL(0x0810B134, 0x03000CC0, 0, 0);
  CALL(0x0810AFF0, 0x03001D00, 0, 0);
  CALL(0x0810B2D0, 0x0095FC00, 0, 0);
  for (uint32_t index = 0; index < 4; ++index) {
    uint32_t entry = 0x08A69038u + index * 12u;
    uint32_t player = R32(entry);
    uint32_t tracks = R32(entry + 4);
    uint32_t count = R8(entry + 8);
    CALL(0x0810B474, player, tracks, count);
    W8(player + 11, R16(entry + 10));
    W32(player + 24, 0x03001EC0);
  }
  return 0;
}

uint32_t Dbaa_AudioMain(const DbaaMusicHost *host) {
  CALL(0x0810A084, 0, 0, 0);
  return 0;
}

uint32_t Dbaa_MusicStartSong(const DbaaMusicHost *host, uint32_t song) {
  uint32_t entry = 0x08A69068u + (song & 65535u) * 8u;
  uint32_t index = R16(entry + 4);
  uint32_t player = R32(0x08A69038u + index * 12u);
  uint32_t header = R32(entry);
  return CALL(0x0810B4EC, player, header, 0);
}

uint32_t Dbaa_MusicPlayerStart(const DbaaMusicHost *host, uint32_t player,
                               uint32_t header) {
  if (R32(player + 0x34) != 0x68736D53u)
    return 0;
  uint32_t check = R8(player + 11), priority = R8(header + 2);
  if (check) {
    int busy = 0;
    if (R32(player))
      busy = !!(R8(R32(player + 0x2C)) & 0x40);
    if (!busy) {
      uint32_t status = R32(player + 4);
      busy = R16(player + 4) && !(status & 0x80000000u);
    }
    if (busy) {
      priority = R8(header + 2);
      if (R8(player + 9) > priority)
        return 0;
    }
  }
  W32(player + 0x34, R32(player + 0x34) + 1u);
  W32(player + 4, 0);
  W32(player, header);
  W32(player + 0x30, R32(header + 4));
  W8(player + 9, priority);
  W32(player + 12, 0);
  W16(player + 0x1C, 150);
  W16(player + 0x20, 150);
  W16(player + 0x1E, 256);
  W16(player + 0x22, 0);
  W16(player + 0x24, 0);
  uint32_t i = 0, track = R32(player + 0x2C), limit = R8(header);
  if (i >= limit)
    goto remaining;
  if (i >= R8(player + 8))
    goto mode;
start:
  Dbaa_MusicTrackStop(host, player, track);
  W8(track, 0xC0);
  W32(track + 0x20, 0);
  W32(track + 0x40, R32(header + 8 + i * 4u));
  ++i;
  track += 80;
  limit = R8(header);
  if (i >= limit)
    goto remaining;
  if (i < R8(player + 8))
    goto start;
remaining:
  while (i < R8(player + 8)) {
    Dbaa_MusicTrackStop(host, player, track);
    W8(track, 0);
    ++i;
    track += 80;
  }
mode:
  if (R8(header + 3) & 0x80)
    Dbaa_SoundMode(host, R8(header + 3));
  W32(player + 0x34, 0x68736D53u);
  return 0;
}

uint32_t Dbaa_MusicPlayerStop(const DbaaMusicHost *host, uint32_t player) {
  uint32_t lock = R32(player + 0x34);
  if (lock != 0x68736D53u)
    return 0;
  W32(player + 0x34, lock + 1u);
  W32(player + 4, R32(player + 4) | 0x80000000u);
  uint32_t count = R8(player + 8), track = R32(player + 0x2C);
  while (count--) {
    Dbaa_MusicTrackStop(host, player, track);
    track += 80;
  }
  W32(player + 0x34, 0x68736D53u);
  return 0;
}

uint32_t Dbaa_MusicStopAll(const DbaaMusicHost *host) {
  for (uint32_t i = 0; i < 4; ++i)
    Dbaa_MusicPlayerStop(host, R32(0x08A69038u + i * 12u));
  return 0;
}

uint32_t Dbaa_MusicPlayerOpen(const DbaaMusicHost *host, uint32_t player,
                              uint32_t tracks, uint32_t raw_count) {
  uint32_t count = raw_count & 255u;
  if (!count)
    return 0;
  if (count > 16)
    count = 16;
  uint32_t sound = R32(0x03007FF0);
  uint32_t lock = R32(sound);
  if (lock != 0x68736D53u)
    return 0;
  W32(sound, lock + 1u);
  CALL(0x0810B120, player, 0, 0);
  W32(player + 0x2C, tracks);
  W8(player + 8, count);
  W32(player + 4, 0x80000000u);
  for (uint32_t index = 0; index < count; ++index)
    W8(tracks + index * 80u, 0);
  uint32_t callback = R32(sound + 0x20);
  if (callback) {
    W32(player + 0x38, callback);
    W32(player + 0x3C, R32(sound + 0x24));
    W32(sound + 0x20, 0);
  }
  W32(sound + 0x24, player);
  W32(sound + 0x20, 0x0810A725);
  W32(sound, 0x68736D53u);
  W32(player + 0x34, 0x68736D53u);
  return 0;
}

uint32_t Dbaa_SoundInitialize(const DbaaMusicHost *host, uint32_t sound) {
  W32(sound, 0);
  if (R32(0x040000C4) & 0x02000000u)
    W32(0x040000C4, 0x84400004u);
  if (R32(0x040000D0) & 0x02000000u)
    W32(0x040000D0, 0x84400004u);
  W16(0x040000C6, 0x400);
  W16(0x040000D2, 0x400);
  W16(0x04000084, 0x8F);
  W16(0x04000082, 0xA90E);
  W8(0x04000089, (R8(0x04000089) & 0x3Fu) | 0x40u);
  W32(0x040000BC, sound + 0x350);
  W32(0x040000C0, 0x040000A0);
  W32(0x040000C8, sound + 0x980);
  W32(0x040000CC, 0x040000A4);
  W32(0x03007FF0, sound);
  /* CpuSet 0x050003EC: clear all 0xFB0 bytes of SoundInfo and PCM. */
  for (uint32_t offset = 0; offset < 0xFB0; offset += 4)
    W32(sound + offset, 0);
  W8(sound + 6, 8);
  W8(sound + 7, 15);
  W32(sound + 0x38, 0x0810AA01);
  W32(sound + 0x28, 0x0810C225);
  W32(sound + 0x2C, 0x0810C225);
  W32(sound + 0x30, 0x0810C225);
  W32(sound + 0x3C, 0x0810C225);
  CALL(0x0810A514, 0x03001C70, 0, 0);
  W32(sound + 0x34, 0x03001C70);
  CALL(0x0810B22C, 0x40000, 0, 0);
  W32(sound, 0x68736D53u);
  return 0;
}

uint32_t Dbaa_SoundExtend(const DbaaMusicHost *host, uint32_t channels) {
  W16(0x04000084, 0x8F);
  W16(0x04000080, 0);
  W8(0x04000063, 8);
  W8(0x04000069, 8);
  W8(0x04000079, 8);
  W8(0x04000065, 0x80);
  W8(0x0400006D, 0x80);
  W8(0x0400007D, 0x80);
  W8(0x04000070, 0);
  W8(0x04000080, 0x77);
  uint32_t sound = R32(0x03007FF0);
  uint32_t lock = R32(sound);
  if (lock != 0x68736D53u)
    return 0;
  W32(sound, lock + 1u);
  W32(0x03001C70 + 8 * 4, 0x0810BFAD);
  W32(0x03001C70 + 17 * 4, 0x0810AC69);
  W32(0x03001C70 + 19 * 4, 0x0810AC7D);
  W32(0x03001C70 + 28 * 4, 0x0810C105);
  W32(0x03001C70 + 29 * 4, 0x0810AC01);
  W32(0x03001C70 + 30 * 4, 0x0810B22D);
  W32(0x03001C70 + 31 * 4, 0x0810A98D);
  W32(0x03001C70 + 32 * 4, 0x0810B611);
  W32(0x03001C70 + 33 * 4, 0x0810B6D9);
  W32(sound + 0x1C, channels);
  W32(sound + 0x28, 0x0810B8ED);
  W32(sound + 0x2C, 0x0810B835);
  W32(sound + 0x30, 0x0810B78D);
  W8(sound + 0x0C, 0);
  /* CpuSet 0x05000040: four 64-byte CGB channel records. */
  for (uint32_t offset = 0; offset < 0x100; offset += 4)
    W32(channels + offset, 0);
  W8(channels + 1, 1);
  W8(channels + 0x1C, 0x11);
  W8(channels + 0x41, 2);
  W8(channels + 0x5C, 0x22);
  W8(channels + 0x81, 3);
  W8(channels + 0x9C, 0x44);
  W8(channels + 0xC1, 4);
  W8(channels + 0xDC, 0x88);
  W32(sound, lock);
  return 0;
}

uint32_t Dbaa_CgbStop(const DbaaMusicHost *host, uint32_t channel) {
  switch (channel & 255) {
  case 1:
    W8(0x04000063, 8);
    W8(0x04000065, 0x80);
    break;
  case 2:
    W8(0x04000069, 8);
    W8(0x0400006D, 0x80);
    break;
  case 3:
    W8(0x04000070, 0);
    break;
  default:
    W8(0x04000079, 8);
    W8(0x0400007D, 0x80);
    break;
  }
  return 0;
}

uint32_t Dbaa_CgbUpdateVolume(const DbaaMusicHost *host, uint32_t channel) {
  uint32_t right = R8(channel + 2), left = R8(channel + 3);
  uint32_t directional = 0, pan = 255;
  if (right >= left && right / 2 >= left) {
    pan = 15;
    directional = 1;
  } else if (right < left && left / 2 >= right) {
    pan = 240;
    directional = 1;
  }
  W8(channel + 0x1B, pan);
  left = R8(channel + 3);
  right = R8(channel + 2);
  uint32_t volume = (left + right) >> 4;
  W8(channel + 0x0A, volume);
  if (directional && volume > 15)
    W8(channel + 0x0A, 15);
  uint32_t sustain = R8(channel + 6);
  volume = R8(channel + 0x0A);
  W8(channel + 0x19, (sustain * volume + 15) >> 4);
  uint32_t mask = R8(channel + 0x1C);
  pan = R8(channel + 0x1B);
  W8(channel + 0x1B, mask & pan);
  return 0;
}

uint32_t Dbaa_CgbUpdate(const DbaaMusicHost *host) {
  uint32_t sound = R32(0x03007FF0);
  uint32_t tick = R8(sound + 0x0A);
  W8(sound + 0x0A, tick ? tick - 1u : 14);
  uint32_t channel = R32(sound + 0x1C);
  for (uint32_t number = 1; number <= 4; ++number, channel += 64) {
    uint32_t status = R8(channel);
    if (!(status & 0xC7))
      continue;
    uint32_t reg0, reg1, reg2, reg3, reg4;
    switch (number) {
    case 1:
      reg0 = 0x04000060;
      reg1 = 0x04000062;
      reg2 = 0x04000063;
      reg3 = 0x04000064;
      reg4 = 0x04000065;
      break;
    case 2:
      reg0 = 0x04000061;
      reg1 = 0x04000068;
      reg2 = 0x04000069;
      reg3 = 0x0400006C;
      reg4 = 0x0400006D;
      break;
    case 3:
      reg0 = 0x04000070;
      reg1 = 0x04000072;
      reg2 = 0x04000073;
      reg3 = 0x04000074;
      reg4 = 0x04000075;
      break;
    default:
      reg0 = 0x04000071;
      reg1 = 0x04000078;
      reg2 = 0x04000079;
      reg3 = 0x0400007C;
      reg4 = 0x0400007D;
      break;
    }
    int32_t counter = (int32_t)R8(sound + 0x0A);
    uint32_t envelope = R8(reg2), value, wave;
    if (status & 0x80) {
      if (status & 0x40)
        goto stop_channel;
      W8(channel, 3);
      W8(channel + 0x1D, 3);
      CALL(0x0810B884, channel, 0, 0);
      switch (number) {
      case 1:
        W8(reg0, R8(channel + 0x1F));
        /* fall through */
      case 2:
        value = R32(channel + 0x24) << 6;
        value += R8(channel + 0x1E);
        W8(reg1, value);
        break;
      case 3:
        wave = R32(channel + 0x24);
        value = R32(channel + 0x28);
        if (wave != value) {
          W8(reg0, 0x40);
          wave = R32(channel + 0x24);
          for (uint32_t offset = 0; offset < 16; offset += 4) {
            value = R32(wave + offset);
            W32(0x04000090 + offset, value);
          }
          W32(channel + 0x28, wave);
        }
        W8(reg0, 0);
        W8(reg1, R8(channel + 0x1E));
        value = R8(channel + 0x1E) ? 0xC0 : 0x80;
        W8(channel + 0x1A, value);
        goto initialize_envelope;
      default:
        W8(reg1, R8(channel + 0x1E));
        W8(reg3, R32(channel + 0x24) << 3);
        break;
      }
      envelope = R8(channel + 4) + 8;
      value = R8(channel + 0x1E);
      W8(channel + 0x1A, value ? 0x40 : 0);
    initialize_envelope:
      value = R8(channel + 4);
      W8(channel + 0x0B, value);
      if (!value)
        goto attack_complete;
      W8(channel + 9, 0);
      goto decrement_envelope;
    }
    if (status & 4) {
      value = (R8(channel + 0x0D) - 1u) & 255;
      W8(channel + 0x0D, value);
      if (s8(value) > 0)
        goto write_hardware;
    stop_channel:
      CALL(0x0810B834, number, 0, 0);
      W8(channel, 0);
      goto clear_flags;
    }
    if ((status & 0x40) && (status & 3)) {
      W8(channel, status & 0xFC);
      value = R8(channel + 7);
      W8(channel + 0x0B, value);
      if (!value)
        goto start_echo;
      W8(channel + 0x1D, R8(channel + 0x1D) | 1);
      if (number != 3)
        envelope = R8(channel + 7);
      goto decrement_envelope;
    }
  process_envelope:
    if (R8(channel + 0x0B))
      goto decrement_envelope;
    if (number == 3)
      W8(channel + 0x1D, R8(channel + 0x1D) | 1);
    CALL(0x0810B884, channel, 0, 0);
    value = R8(channel) & 3;
    if (!value) {
      value = (R8(channel + 9) - 1u) & 255;
      W8(channel + 9, value);
      if (s8(value) <= 0)
        goto start_echo;
      value = R8(channel + 7);
      goto store_counter;
    }
    if (value == 1)
      goto reload_sustain;
    if (value == 2) {
      value = (R8(channel + 9) - 1u) & 255;
      W8(channel + 9, value);
      uint32_t goal = R8(channel + 0x19);
      if (s8(value) > s8(goal)) {
        value = R8(channel + 5);
        goto store_counter;
      }
      goto decay_complete;
    }
    value = (R8(channel + 9) + 1u) & 255;
    W8(channel + 9, value);
    if (value < R8(channel + 0x0A)) {
      value = R8(channel + 4);
      goto store_counter;
    }
  attack_complete:
    W8(channel, R8(channel) - 1u);
    value = R8(channel + 5);
    W8(channel + 0x0B, value);
    if (!value)
      goto decay_complete;
    W8(channel + 0x1D, R8(channel + 0x1D) | 1);
    W8(channel + 9, R8(channel + 0x0A));
    if (number != 3)
      envelope = R8(channel + 5);
    goto decrement_envelope;
  decay_complete:
    if (!R8(channel + 6)) {
      W8(channel, R8(channel) & 0xFC);
      goto start_echo;
    }
    W8(channel, R8(channel) - 1u);
    W8(channel + 0x1D, R8(channel + 0x1D) | 1);
    if (number != 3)
      envelope = 8;
  reload_sustain:
    W8(channel + 9, R8(channel + 0x19));
    value = 7;
  store_counter:
    W8(channel + 0x0B, value);
  decrement_envelope:
    W8(channel + 0x0B, R8(channel + 0x0B) - 1u);
    if (!counter) {
      --counter;
      goto process_envelope;
    }
    goto write_hardware;
  start_echo:
    value = R8(channel + 0x0C);
    value = (value * R8(channel + 0x0A) + 255) >> 8;
    W8(channel + 9, value);
    if (!value)
      goto stop_channel;
    W8(channel, R8(channel) | 4);
    W8(channel + 0x1D, R8(channel + 0x1D) | 1);
    if (number != 3)
      envelope = 8;
  write_hardware:
    if (R8(channel + 0x1D) & 2) {
      if (number <= 3 && (R8(channel + 1) & 8)) {
        value = R8(0x04000089);
        if (value <= 0x7F) {
          uint32_t frequency = R32(channel + 0x20);
          W32(channel + 0x20, value <= 0x3F ? (frequency + 2u) & 0x7FCu
                                            : (frequency + 1u) & 0x7FEu);
        }
      }
      if (number == 4) {
        value = R8(reg3) & 8;
        value |= R32(channel + 0x20);
      } else {
        value = R32(channel + 0x20);
      }
      W8(reg3, value);
      value = R8(channel + 0x1A) & 0xC0;
      value += R8(channel + 0x21);
      W8(channel + 0x1A, value);
      W8(reg4, value & 255);
    }
    if (R8(channel + 0x1D) & 1) {
      value = R8(0x04000081);
      value &= ~R8(channel + 0x1C);
      value |= R8(channel + 0x1B);
      W8(0x04000081, value);
      if (number == 3) {
        value = R8(channel + 9);
        W8(reg2, R8(0x08A676C4 + value));
        if (R8(channel + 0x1A) & 0x80) {
          W8(reg0, 0x80);
          W8(reg4, R8(channel + 0x1A));
          W8(channel + 0x1A, R8(channel + 0x1A) & 0x7F);
        }
      } else {
        envelope &= 15;
        value = R8(channel + 9) << 4;
        W8(reg2, value + envelope);
        W8(reg4, R8(channel + 0x1A) | 0x80);
        if (number == 1 && !(R8(reg0) & 8))
          W8(reg4, R8(channel + 0x1A) | 0x80);
      }
    }
  clear_flags:
    W8(channel + 0x1D, 0);
  }
  return 0;
}

#include "pcm_mixer_impl.h"

uint32_t Dbaa_AudioCall(const DbaaMusicHost *host, uint32_t target, uint32_t a0,
                        uint32_t a1, uint32_t a2) {
  switch (target & ~1u) {
  case 0x0810A084:
    return Dbaa_SoundMain(host);
  case 0x0810A724:
    Dbaa_MusicPlayerUpdate(host, a0);
    return 0;
  case 0x0810AD34:
    return Dbaa_AudioInitialize(host);
  case 0x0810ADAC:
    return Dbaa_AudioMain(host);
  case 0x0810ADB8:
    return Dbaa_MusicStartSong(host, a0);
  case 0x0810AEEC:
    return Dbaa_MusicStopAll(host);
  case 0x0810B4EC:
    return Dbaa_MusicPlayerStart(host, a0, a1);
  case 0x0810B5D0:
    return Dbaa_MusicPlayerStop(host, a0);
  case 0x0810B474:
    return Dbaa_MusicPlayerOpen(host, a0, a1, a2);
  case 0x0810A4AC:
    return Dbaa_AudioClear64(host, a0);
  case 0x0810A4C4:
    return Dbaa_AudioUnlinkChannel(host, a0);
  case 0x0810A4E4:
    return Dbaa_MusicEventFine(host, a0, a1);
  case 0x0810A514:
    return Dbaa_SoundCopyCommandTable(host, a0);
  case 0x0810A548:
    return Dbaa_MusicReadCommandFiltered(host, a0, a1);
  case 0x0810A574:
    return Dbaa_MusicEventPattern(host, a0, a1);
  case 0x0810A590:
    return Dbaa_MusicEventPatternEnd(host, a0, a1);
  case 0x0810A5A4:
    return Dbaa_MusicEventRepeat(host, a0, a1);
  case 0x0810A5D4:
    return Dbaa_MusicEventPriority(host, a0, a1);
  case 0x0810A5E0:
    return Dbaa_MusicEventTempo(host, a0, a1);
  case 0x0810A5F4:
    return Dbaa_MusicEventKeyShift(host, a0, a1);
  case 0x0810A608:
    return Dbaa_MusicEventVoice(host, a0, a1);
  case 0x0810A638:
    return Dbaa_MusicEventVolume(host, a0, a1);
  case 0x0810A64C:
    return Dbaa_MusicEventPan(host, a0, a1);
  case 0x0810A660:
    return Dbaa_MusicEventPitchBend(host, a0, a1);
  case 0x0810A674:
    return Dbaa_MusicEventBendRange(host, a0, a1);
  case 0x0810A688:
    return Dbaa_MusicEventLfoDelay(host, a0, a1);
  case 0x0810A694:
    return Dbaa_MusicEventModType(host, a0, a1);
  case 0x0810A6AC:
    return Dbaa_MusicEventTune(host, a0, a1);
  case 0x0810A6C0:
    return Dbaa_MusicEventPort(host, a0, a1);
  case 0x0810A554:
    return Dbaa_MusicEventGoto(host, a0, a1);
  case 0x0810A98C:
    return Dbaa_MusicTrackStop(host, a0, a1);
  case 0x0810AA00:
    return Dbaa_SoundUpdateTrack(host, a0, a1, a2);
  case 0x0810AC00:
    return Dbaa_MusicEventEndTie(host, a0, a1);
  case 0x0810AC40:
    return Dbaa_MusicClearModulation(host, a0, a1);
  case 0x0810AC5C:
    return Dbaa_MusicReadCommandByte(host, a0, a1);
  case 0x0810AC68:
    return Dbaa_MusicEventLfoSpeed(host, a0, a1);
  case 0x0810AC7C:
    return Dbaa_MusicEventModDepth(host, a0, a1);
  case 0x0810AC90:
    return Dbaa_MusicCalculateFrequency(host, a0, a1, a2);
  case 0x0810B78C:
    return Dbaa_CgbCalculateFrequency(host, a0, a1, a2);
  case 0x0810B10C:
    return CALL(R32(0x03001CF8), a0, 0, 0);
  case 0x0810B120:
    return CALL(R32(0x03001CFC), a0, 0, 0);
  case 0x0810B134:
    return Dbaa_SoundInitialize(host, a0);
  case 0x0810AFF0:
    return Dbaa_SoundExtend(host, a0);
  case 0x0810B22C:
    return Dbaa_SoundSetFrequency(host, a0);
  case 0x0810B2D0:
    return Dbaa_SoundMode(host, a0);
  case 0x0810B3BC:
    return Dbaa_SoundVSyncOff(host);
  case 0x0810B438:
    return Dbaa_SoundVSyncOn(host);
  case 0x0810B610:
    return Dbaa_MusicFadeOutBody(host, a0);
  case 0x0810B6D8:
    return Dbaa_MusicTrackVolumePitch(host, a0, a1);
  case 0x0810BFAC:
    return Dbaa_MusicEventMemoryAccess(host, a0, a1);
  case 0x0810C104:
    return Dbaa_MusicEventExtended(host, a0, a1);
  case 0x0810C124:
    return Dbaa_MusicEventExtendedEnd(host, a0, a1);
  case 0x0810C138:
    return Dbaa_MusicEventWave(host, a0, a1);
  case 0x0810C180:
    return music_event_set_byte(host, a1, 0x24);
  case 0x0810C194:
    return music_event_set_byte(host, a1, 0x2C);
  case 0x0810C1A8:
    return music_event_set_byte(host, a1, 0x2D);
  case 0x0810C1BC:
    return music_event_set_byte(host, a1, 0x2E);
  case 0x0810C1D0:
    return music_event_set_byte(host, a1, 0x2F);
  case 0x0810C1E4:
    return music_event_set_byte(host, a1, 0x1E);
  case 0x0810C1F0:
    return music_event_set_byte(host, a1, 0x1F);
  case 0x0810C1FC:
    return music_event_set_byte(host, a1, 0x26);
  case 0x0810C210:
    return music_event_set_byte(host, a1, 0x27);
  case 0x0810C224:
    return 0;
  case 0x0810B834:
    return Dbaa_CgbStop(host, a0);
  case 0x0810B884:
    return Dbaa_CgbUpdateVolume(host, a0);
  case 0x0810B8EC:
    return Dbaa_CgbUpdate(host);
  default:
    return host->call(host->user, target, a0, a1, a2);
  }
}

uint32_t Dbaa_MusicEventEndTie(const DbaaMusicHost *host, uint32_t player,
                               uint32_t track) {
  (void)player;
  uint32_t command = R32(track + 0x40), key = R8(command);
  if (key < 0x80) {
    W8(track + 5, key);
    W32(track + 0x40, command + 1);
  } else {
    key = R8(track + 5);
  }
  uint32_t channel = R32(track + 0x20);
  while (channel) {
    uint32_t status = R8(channel);
    if ((status & 0x83) && !(status & 0x40) && R8(channel + 0x11) == key) {
      W8(channel, status | 0x40);
      break;
    }
    channel = R32(channel + 0x34);
  }
  return 0;
}

uint32_t Dbaa_MusicClearModulation(const DbaaMusicHost *host, uint32_t player,
                                   uint32_t track) {
  (void)player;
  W8(track + 0x16, 0);
  W8(track + 0x1A, 0);
  uint32_t flags = R8(track + 0x18) ? 3 : 12;
  W8(track, R8(track) | flags);
  return 0;
}

uint32_t Dbaa_MusicReadCommandByte(const DbaaMusicHost *host, uint32_t player,
                                   uint32_t track) {
  (void)player;
  uint32_t command = R32(track + 0x40);
  /* The SDK increments the cursor before reading, including aliased input. */
  W32(track + 0x40, command + 1);
  return R8(command);
}

uint32_t Dbaa_MusicEventLfoSpeed(const DbaaMusicHost *host, uint32_t player,
                                 uint32_t track) {
  uint32_t speed = CALL(0x0810AC5C, player, track, 0);
  W8(track + 0x19, speed);
  if (!speed)
    CALL(0x0810AC40, player, track, 0);
  return 0;
}

uint32_t Dbaa_MusicEventModDepth(const DbaaMusicHost *host, uint32_t player,
                                 uint32_t track) {
  uint32_t depth = CALL(0x0810AC5C, player, track, 0);
  W8(track + 0x17, depth);
  if (!depth)
    CALL(0x0810AC40, player, track, 0);
  return 0;
}

uint32_t Dbaa_MusicEventMemoryAccess(const DbaaMusicHost *host, uint32_t player,
                                     uint32_t track) {
  uint32_t command = R32(track + 0x40), op = R8(command);
  W32(track + 0x40, command + 1);
  uint32_t base = R32(player + 0x18);
  uint32_t address = base + R8(command + 1);
  W32(track + 0x40, command + 2);
  uint32_t data = R8(command + 2);
  W32(track + 0x40, command + 3);
  uint32_t left, right, taken;
  switch (op) {
  case 0:
    W8(address, data);
    return 0;
  case 1:
    W8(address, R8(address) + data);
    return 0;
  case 2:
    W8(address, R8(address) - data);
    return 0;
  case 3:
    W8(address, R8(R32(player + 0x18) + data));
    return 0;
  case 4:
  case 5:
    base = R32(player + 0x18) + data;
    left = R8(address);
    right = R8(base);
    W8(address, op == 4 ? left + right : left - right);
    return 0;
  default:
    if (op > 17)
      return 0;
  }
  if (op >= 12) {
    base = R32(player + 0x18) + data;
    left = R8(address);
    right = R8(base);
  } else {
    left = R8(address);
    right = data;
  }
  switch ((op - 6) % 6) {
  case 0:
    taken = left == right;
    break;
  case 1:
    taken = left != right;
    break;
  case 2:
    taken = left > right;
    break;
  case 3:
    taken = left >= right;
    break;
  case 4:
    taken = left <= right;
    break;
  default:
    taken = left < right;
    break;
  }
  if (taken)
    CALL(R32(0x03001C74), player, track, 0);
  else
    W32(track + 0x40, R32(track + 0x40) + 4);
  return 0;
}

uint32_t Dbaa_MusicEventExtended(const DbaaMusicHost *host, uint32_t player,
                                 uint32_t track) {
  uint32_t command = R32(track + 0x40), index = R8(command);
  W32(track + 0x40, command + 1);
  return CALL(R32(0x08A67708 + index * 4), player, track, 0);
}

uint32_t Dbaa_MusicEventExtendedEnd(const DbaaMusicHost *host, uint32_t player,
                                    uint32_t track) {
  return CALL(R32(0x03001C70), player, track, 0);
}

uint32_t Dbaa_MusicEventWave(const DbaaMusicHost *host, uint32_t player,
                             uint32_t track) {
  (void)player;
  uint32_t command = R32(track + 0x40);
  uint32_t wave = R8(command);
  wave |= R8(command + 1) << 8;
  wave |= R8(command + 2) << 16;
  wave |= R8(command + 3) << 24;
  W32(track + 0x28, wave);
  W32(track + 0x40, command + 4);
  return 0;
}

uint32_t Dbaa_MusicEventGoto(const DbaaMusicHost *host, uint32_t player,
                             uint32_t track) {
  (void)player;
  uint32_t command = R32(track + 0x40);
  uint32_t destination = R8(command + 3) << 24;
  destination |= R8(command + 2) << 16;
  destination |= R8(command + 1) << 8;
  destination |= Dbaa_AudioReadByte(host, command);
  W32(track + 0x40, destination);
  return 0;
}

static void note_channel_volume(const DbaaMusicHost *host, uint32_t channel,
                                uint32_t track) {
  uint32_t velocity = R8(channel + 0x12);
  int32_t pan = s8(R8(channel + 0x14));
  uint32_t right = (uint32_t)(128 + pan) * velocity * R8(track + 0x10) >> 14;
  W8(channel + 2, right > 255 ? 255 : right);
  uint32_t left = (uint32_t)(127 - pan) * velocity * R8(track + 0x11) >> 14;
  W8(channel + 3, left > 255 ? 255 : left);
}

uint32_t Dbaa_SoundUpdateTrack(const DbaaMusicHost *host, uint32_t duration,
                               uint32_t player, uint32_t track) {
  uint32_t sound = R32(0x03007FF0);
  W8(track + 4, R8(0x08A676D4 + duration));
  uint32_t command = R32(track + 0x40), value = R8(command);
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
  int32_t rhythm_pan = 0;
  uint32_t tone = track + 0x24, type = R8(tone), key;
  if (type & 0xC0) {
    key = R8(track + 5);
    uint32_t index = (type & 0x40) ? R8(R32(track + 0x2C) + key) : key;
    tone = R32(track + 0x28) + 12 * index;
    if (R8(tone) & 0xC0)
      return 0;
    if (type & 0x80) {
      value = R8(tone + 3);
      if (value & 0x80)
        rhythm_pan = ((int32_t)value - 0xC0) * 2;
      key = R8(tone + 1);
    }
  } else {
    key = R8(track + 5);
  }
  uint32_t priority = R8(player + 9);
  priority += R8(track + 0x1D);
  if (priority > 255)
    priority = 255;
  uint32_t cgb = R8(tone) & 7, channel;
  if (cgb) {
    channel = R32(sound + 0x1C);
    if (!channel)
      return 0;
    channel += (cgb - 1) * 64;
    uint32_t status = R8(channel);
    if ((status & 0xC7) && !(status & 0x40)) {
      uint32_t current_priority = R8(channel + 0x13);
      if (current_priority > priority ||
          (current_priority == priority && R32(channel + 0x2C) < track))
        return 0;
    }
  } else {
    uint32_t chosen = 0, best_priority = priority, best_track = track;
    uint32_t releasing = 0;
    int32_t count = (int32_t)R8(sound + 6);
    channel = sound + 0x50;
    /* Like the original, inspect the first channel even when count is zero. */
    do {
      uint32_t status = R8(channel);
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
      uint32_t current_priority = R8(channel + 0x13);
      if (current_priority < best_priority) {
        best_priority = current_priority;
        best_track = R32(channel + 0x2C);
        chosen = channel;
      } else if (current_priority == best_priority) {
        uint32_t owner = R32(channel + 0x2C);
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
      return 0;
  }
selected:
  CALL(0x0810B10C, channel, 0, 0);
  W32(channel + 0x30, 0);
  uint32_t old_head = R32(track + 0x20);
  W32(channel + 0x34, old_head);
  if (old_head)
    W32(old_head + 0x30, channel);
  W32(track + 0x20, channel);
  W32(channel + 0x2C, track);
  value = R8(track + 0x1B);
  W8(track + 0x1C, value);
  if (value)
    Dbaa_MusicClearModulation(host, player, track);
  Dbaa_MusicTrackVolumePitch(host, player, track);
  W32(channel + 0x10, R32(track + 4));
  W8(channel + 0x13, priority);
  W8(channel + 8, key);
  W8(channel + 0x14, (uint32_t)rhythm_pan);
  W8(channel + 1, R8(tone));
  uint32_t wave = R32(tone + 4);
  W32(channel + 0x24, wave);
  W32(channel + 4, R32(tone + 8));
  W16(channel + 0xC, R16(track + 0x1E));
  note_channel_volume(host, channel, track);
  int32_t pitch_key = (int32_t)R8(channel + 8) + s8(R8(track + 8));
  if (pitch_key < 0)
    pitch_key = 0;
  uint32_t frequency;
  if (cgb) {
    W8(channel + 0x1E, R8(tone + 2));
    uint32_t sweep = R8(tone + 3);
    if ((sweep & 0x80) || !(sweep & 0x70))
      sweep = 8;
    W8(channel + 0x1F, sweep);
    frequency =
        CALL(R32(sound + 0x30), cgb, (uint32_t)pitch_key, R8(track + 9));
  } else {
    frequency = Dbaa_MusicCalculateFrequency(host, wave, (uint32_t)pitch_key,
                                             R8(track + 9));
  }
  W32(channel + 0x20, frequency);
  W8(channel, 0x80);
  W8(track, R8(track) & 0xF0);
  return 0;
}
