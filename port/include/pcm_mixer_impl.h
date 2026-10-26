/* Semantic PCM mixer. Included by audio_helpers.c and the excluded GBA C probe.
 * The packed accumulators reproduce 32-bit wrap and partial-word rotation.
 * No ARM code, CPU interpreter, floating point, or saturating approximation. */
#ifndef DBAA_PCM_MIXER_IMPL_H
#define DBAA_PCM_MIXER_IMPL_H

static int32_t pcm_signed(uint32_t value) {
  return value < 0x80000000u ? (int32_t)value : -1 - (int32_t)~value;
}

static uint32_t pcm_asr(uint32_t value, uint32_t shift) {
  return (value >> shift) |
         ((value & 0x80000000u) ? (~0u << (32 - shift)) : 0u);
}

static uint32_t pcm_ror(uint32_t value, uint32_t shift) {
  shift &= 31;
  return shift ? (value >> shift) | (value << (32 - shift)) : value;
}

static uint32_t pcm_signed_byte(uint32_t value) {
  return (value & 128) ? value | 0xFFFFFF00u : value;
}

static uint32_t pcm_accumulate(uint32_t packed, uint32_t volume,
                               uint32_t sample) {
  return ((volume * sample) & ~0x00FF0000u) + pcm_ror(packed, 8);
}

#ifndef DBAA_MIXER_ARGUMENTS
#define DBAA_MIXER_ARGUMENTS const DbaaMusicHost *host
#endif

uint32_t Dbaa_SoundMain(DBAA_MIXER_ARGUMENTS) {
  uint32_t sound = R32(0x03007FF0);
  uint32_t lock = R32(sound);
  if (lock != 0x68736D53u)
    return 0;
  W32(sound, lock + 1u);
  uint32_t deadline = R8(sound + 12);
  if (deadline) {
    uint32_t line = R8(0x04000006);
    deadline += line < 160 ? line + 228 : line;
  }
  uint32_t callback = R32(sound + 0x20);
  if (callback)
    CALL(callback, R32(sound + 0x24), 0, 0);
  callback = R32(sound + 0x28);
  CALL(callback, sound, 0, 0);
  uint32_t frames = R32(sound + 16);
  uint32_t pcm = sound + 0x350;
  uint32_t dma = R8(sound + 4);
  if (dma > 1) {
    uint32_t period = R8(sound + 11);
    pcm += frames * (period - (dma - 1u));
  }
  uint32_t reverb = R8(sound + 5);
  if (reverb) {
    uint32_t next = dma == 2 ? sound + 0x350 : pcm + frames;
    uint32_t output = pcm, remaining = frames;
    do {
      uint32_t sample = pcm_signed_byte(R8(output + 0x630));
      sample += pcm_signed_byte(R8(output));
      sample += pcm_signed_byte(R8(next + 0x630));
      sample += pcm_signed_byte(R8(next++));
      sample = pcm_asr(sample * reverb, 9);
      if (sample & 128)
        ++sample;
      W8(output + 0x630, sample);
      W8(output++, sample);
    } while (pcm_signed(--remaining) > 0);
  } else {
    /* Preserve the original interleaved word clears, including short tails. */
    uint32_t output = pcm, right = pcm + 0x630, groups = frames >> 3;
    if (frames & 4) {
      W32(output, 0);
      output += 4;
      W32(right, 0);
      right += 4;
    }
    uint32_t pairs = groups >> 1;
    if (groups & 1) {
      for (uint32_t i = 0; i < 2; ++i) {
        W32(output, 0);
        output += 4;
        W32(right, 0);
        right += 4;
      }
    }
    do {
      for (uint32_t i = 0; i < 4; ++i) {
        W32(output, 0);
        output += 4;
        W32(right, 0);
        right += 4;
      }
    } while (pcm_signed(--pairs) > 0);
  }
  uint32_t reciprocal = R32(sound + 24);
  uint32_t channels = R8(sound + 6), channel = sound + 0x50;
  do {
    uint32_t wave = R32(channel + 0x24);
    if (deadline) {
      uint32_t line = R8(0x04000006);
      line = line < 160 ? line + 228 : line;
      if (line >= deadline)
        break;
    }
    uint32_t status = R8(channel);
    if (!(status & 0xC7))
      goto next_channel;
    uint32_t envelope;
    if (status & 128) {
      if (status & 64)
        goto stop_channel;
      status = 3;
      W8(channel, status);
      W32(channel + 0x28, wave + 16);
      W32(channel + 0x18, R32(wave + 12));
      envelope = 0;
      W8(channel + 9, 0);
      W32(channel + 0x1C, 0);
      if (R8(wave + 3) & 0xC0) {
        status |= 16;
        W8(channel, status);
      }
      goto attack;
    }
    envelope = R8(channel + 9);
    if (status & 4) {
      uint32_t length = R8(channel + 13);
      W8(channel + 13, length - 1u);
      if (length <= 1)
        goto stop_channel;
      goto envelope_ready;
    }
    if (status & 64) {
      envelope = envelope * R8(channel + 7) >> 8;
      if (envelope > R8(channel + 12))
        goto envelope_ready;
      goto echo;
    }
    if ((status & 3) == 2) {
      envelope = envelope * R8(channel + 5) >> 8;
      uint32_t sustain = R8(channel + 6);
      if (envelope > sustain)
        goto envelope_ready;
      envelope = sustain;
      if (!sustain)
        goto echo;
      W8(channel, --status);
      goto envelope_ready;
    }
    if ((status & 3) != 3)
      goto envelope_ready;
  attack:
    envelope += R8(channel + 4);
    if (envelope >= 255) {
      envelope = 255;
      W8(channel, --status);
    }
    goto envelope_ready;
  echo:
    envelope = R8(channel + 12);
    if (!envelope) {
    stop_channel:
      W8(channel, 0);
      goto next_channel;
    }
    status |= 4;
    W8(channel, status);
  envelope_ready:
    W8(channel + 9, envelope);
    uint32_t level = (R8(sound + 7) + 1u) * envelope >> 4;
    W8(channel + 10, R8(channel + 2) * level >> 8);
    W8(channel + 11, R8(channel + 3) * level >> 8);
    uint32_t loop_length = status & 16, loop_start = 0;
    if (loop_length) {
      loop_start = wave + 16;
      uint32_t offset = R32(wave + 8);
      loop_start += offset;
      loop_length = R32(wave + 12) - offset;
    }
    uint32_t output = pcm, count = R32(channel + 24);
    uint32_t cursor = R32(channel + 40);
    uint32_t right_volume = R8(channel + 10) << 16;
    uint32_t left_volume = R8(channel + 11) << 16;
    uint32_t fixed = R8(channel + 1) & 8;
    uint32_t budget = frames, left, right, lane;
    if (fixed) {
    fixed_chunk:
      if (pcm_signed(count) > 4) {
        uint32_t tail;
        count -= budget;
        if (pcm_signed(count) > 0) {
          tail = 0;
        } else {
          tail = budget;
          count += budget;
          budget = count - 4u;
          tail -= budget;
          count &= 3;
          if (!count)
            count = 4;
        }
        do {
          left = R32(output);
          right = R32(output + 0x630);
          for (lane = 0; lane < 4; ++lane) {
            uint32_t sample = pcm_signed_byte(R8(cursor++));
            left = pcm_accumulate(left, right_volume, sample);
            right = pcm_accumulate(right, left_volume, sample);
          }
          W32(output + 0x630, right);
          W32(output, left);
          output += 4;
          budget -= 4;
        } while (pcm_signed(budget) > 0);
        budget += tail;
        if (!budget)
          goto save_channel;
      }
      left = R32(output);
      right = R32(output + 0x630);
      for (lane = 0; lane < 4; ++lane) {
        uint32_t sample = pcm_signed_byte(R8(cursor++));
        left = pcm_accumulate(left, right_volume, sample);
        right = pcm_accumulate(right, left_volume, sample);
        if (!--count) {
          count = loop_length;
          if (!count)
            goto sample_end;
          cursor = loop_start;
        }
      }
      W32(output + 0x630, right);
      W32(output, left);
      output += 4;
      budget -= 4;
      if (pcm_signed(budget) > 0)
        goto fixed_chunk;
    } else {
      uint32_t fraction = R32(channel + 28);
      uint32_t step = reciprocal * R32(channel + 32);
      uint32_t sample = pcm_signed_byte(R8(cursor));
      uint32_t difference = pcm_signed_byte(R8(++cursor)) - sample;
      do {
        left = R32(output);
        right = R32(output + 0x630);
        for (lane = 0; lane < 4; ++lane) {
          uint32_t interpolated = sample + pcm_asr(fraction * difference, 23);
          left = pcm_accumulate(left, right_volume, interpolated);
          right = pcm_accumulate(right, left_volume, interpolated);
          fraction += step;
          uint32_t skip = fraction >> 23;
          if (skip) {
            fraction &= ~0x3F800000u;
            count -= skip;
            if (pcm_signed(count) <= 0) {
              if (!loop_length)
                goto sample_end;
              cursor = loop_start;
              uint32_t offset = 0u - count;
              while (pcm_signed(count += loop_length) <= 0)
                offset -= loop_length;
              sample = pcm_signed_byte(R8(cursor += offset));
            } else if (!--skip) {
              sample += difference;
            } else {
              sample = pcm_signed_byte(R8(cursor += skip));
            }
            difference = pcm_signed_byte(R8(++cursor)) - sample;
          }
        }
        W32(output + 0x630, right);
        W32(output, left);
        output += 4;
        budget -= 4;
      } while (pcm_signed(budget) > 0);
      --cursor;
      W32(channel + 28, fraction);
    }
  save_channel:
    W32(channel + 24, count);
    W32(channel + 40, cursor);
    goto next_channel;
  sample_end:
    W8(channel, 0);
    left = pcm_ror(left, (3u - lane) * 8u);
    right = pcm_ror(right, (3u - lane) * 8u);
    W32(output + 0x630, right);
    W32(output, left);
  next_channel:
    channel += 64;
  } while (pcm_signed(--channels) > 0);
  W32(sound, 0x68736D53u);
  return 0;
}
#endif
