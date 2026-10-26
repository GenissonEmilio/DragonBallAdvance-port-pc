/* Standalone binding to mGBA's MPL-2.0 GB/GBA PSG implementation (see
 * docs/native_game_integration.md for the pinned source and build contract).
 * Only chip synthesis, timing and sample buffers are linked, never a CPU.
 * The samples are the chip's raw digital mix, before GBA bias/PWM/filtering. */
#include "psg.h"
#include <mgba/core/timing.h>
#include <mgba/internal/gb/audio.h>
#include <stdlib.h>

struct DbaaPsg {
  struct GBAudio chip;
  struct mTiming timing;
  int32_t relative, next;
  uint8_t status;
  uint16_t registers[32];
  uint64_t cycles, frame_cycle, sample_cycle, last_sample;
  unsigned sample_index, sample_interval;
  uint16_t soundbias;
};

DbaaPsg *Dbaa_PsgCreate(void) {
  DbaaPsg *p = calloc(1, sizeof(*p));
  if (!p)
    return NULL;
  mTimingInit(&p->timing, &p->relative, &p->next);
  p->chip.timing = &p->timing;
  GBAudioInit(&p->chip, 1024, &p->status, GB_AUDIO_GBA);
  GBAudioReset(&p->chip);
  /* GBA reset schedules the frame sequencer at cycle zero. */
  GBAudioUpdateFrame(&p->chip);
  p->frame_cycle = 32768;
  p->sample_cycle = 1024;
  p->sample_interval = 512;
  p->soundbias = 0x0200;
  return p;
}
void Dbaa_PsgDestroy(DbaaPsg *p) {
  if (p) {
    GBAudioDeinit(&p->chip);
    mTimingDeinit(&p->timing);
    free(p);
  }
}
static void flush_samples(DbaaPsg *p, uint64_t timestamp) {
  unsigned maximum = 2u << (p->soundbias >> 14);
  while (p->sample_index < maximum &&
         timestamp >=
             p->last_sample + (p->sample_index + 1) * p->sample_interval) {
    GBAudioRun(&p->chip,
               (int32_t)(p->last_sample + p->sample_index * p->sample_interval),
               15);
    ++p->sample_index;
  }
  if (p->sample_index == maximum) {
    p->last_sample += 1024;
    p->sample_index = 0;
  }
}
int Dbaa_PsgAdvance(DbaaPsg *p, uint64_t target) {
  if (!p || target < p->cycles)
    return 0;
  /* Mirror the GBA's sample events and their priority relative to its frame
   * sequencer. Reading the chip does not clock it at arbitrary host times. */
  for (;;) {
    uint64_t event =
        p->sample_cycle < p->frame_cycle ? p->sample_cycle : p->frame_cycle;
    if (event > target)
      break;
    p->timing.masterCycles = (uint32_t)event;
    if (event == p->frame_cycle) {
      flush_samples(p, event);
      GBAudioUpdateFrame(&p->chip);
      p->frame_cycle += 32768;
    }
    if (event == p->sample_cycle) {
      flush_samples(p, event);
      p->sample_cycle += 1024;
    }
  }
  p->timing.masterCycles = (uint32_t)target;
  p->cycles = target;
  return 1;
}
static void byte_write(DbaaPsg *p, unsigned a, uint8_t v) {
  struct GBAudio *c = &p->chip;
  if (a >= 0x90 && a < 0xA0) {
    unsigned bank = c->enable ? !c->ch3.bank : 1;
    uint8_t *wave = (uint8_t *)c->ch3.wavedata32;
    wave[bank * 16 + a - 0x90] = v;
    return;
  }
  switch (a) {
  case 0x60:
    GBAudioWriteNR10(c, v);
    break;
  case 0x62:
    GBAudioWriteNR11(c, v);
    break;
  case 0x63:
    GBAudioWriteNR12(c, v);
    break;
  case 0x64:
    GBAudioWriteNR13(c, v);
    break;
  case 0x65:
    GBAudioWriteNR14(c, v);
    break;
  case 0x68:
    GBAudioWriteNR21(c, v);
    break;
  case 0x69:
    GBAudioWriteNR22(c, v);
    break;
  case 0x6C:
    GBAudioWriteNR23(c, v);
    break;
  case 0x6D:
    GBAudioWriteNR24(c, v);
    break;
  case 0x70:
    c->ch3.size = (v >> 5) & 1;
    c->ch3.bank = (v >> 6) & 1;
    GBAudioWriteNR30(c, v);
    break;
  case 0x72:
    GBAudioWriteNR31(c, v);
    break;
  case 0x73:
    c->ch3.volume = (v >> 5) & 7;
    break;
  case 0x74:
    GBAudioWriteNR33(c, v);
    break;
  case 0x75:
    GBAudioWriteNR34(c, v);
    break;
  case 0x78:
    GBAudioWriteNR41(c, v);
    break;
  case 0x79:
    GBAudioWriteNR42(c, v);
    break;
  case 0x7C:
    GBAudioWriteNR43(c, v);
    break;
  case 0x7D:
    GBAudioWriteNR44(c, v);
    break;
  case 0x80:
    GBAudioWriteNR50(c, v);
    break;
  case 0x81:
    GBAudioWriteNR51(c, v);
    break;
  case 0x84:
    p->status = (p->status & 15) | (v & 128);
    GBAudioWriteNR52(c, v);
    if (!c->enable) {
      c->ch3.size = c->ch3.bank = c->ch3.volume = 0;
    }
    break;
  default:
    break;
  }
}
static void word_write(DbaaPsg *p, unsigned a, uint32_t v) {
  unsigned bank = p->chip.enable ? !p->chip.ch3.bank : 1;
  GBAudioRun(&p->chip, (int32_t)p->cycles, 4);
  p->chip.ch3.wavedata32[bank * 4 + (a - 0x90) / 4] = v;
  p->registers[(a - 0x60) / 2] = (uint16_t)v;
  p->registers[(a - 0x60) / 2 + 1] = (uint16_t)(v >> 16);
}
static void half_write(DbaaPsg *p, unsigned a, uint16_t v) {
  unsigned slot = (a - 0x60) / 2;
  if (a <= 0x80 && !p->chip.enable)
    return;
  if (a == 0x88) {
    /* The GBA sequencer samples 2/4/8/16 times per 1024-cycle event.
     * Flush at the old rate before changing its index/rate, as the hardware
     * reference does when SOUNDBIAS resolution changes between events. */
    flush_samples(p, p->cycles);
    unsigned old_interval = p->sample_interval;
    p->soundbias = v & 0xC3FE;
    unsigned resolution = p->soundbias >> 14;
    p->sample_interval = 0x200u >> resolution;
    if (old_interval != p->sample_interval) {
      p->sample_index =
          (unsigned)((p->cycles - p->last_sample) >> (9 - resolution));
      if (p->sample_index >= 16)
        p->sample_index = 0;
    }
    p->registers[slot] = p->soundbias;
    return;
  }
  if (a >= 0x90) {
    uint32_t merged = v;
    if (a & 2)
      merged = ((uint32_t)v << 16) | p->registers[slot - 1];
    else
      merged |= (uint32_t)p->registers[slot + 1] << 16;
    word_write(p, a & ~3u, merged);
    return;
  }
  if (a == 0x60 || a == 0x62 || a == 0x64 || a == 0x68 || a == 0x6C ||
      a == 0x70 || a == 0x72 || a == 0x74 || a == 0x78 || a == 0x7C ||
      a == 0x80 || a == 0x84)
    flush_samples(p, p->cycles);
  byte_write(p, a, (uint8_t)v);
  byte_write(p, a + 1, (uint8_t)(v >> 8));
  uint16_t mask = 0;
  switch (a) {
  case 0x60:
    mask = 0x007F;
    break;
  case 0x62:
  case 0x68:
    mask = 0xFFC0;
    break;
  case 0x64:
  case 0x6C:
  case 0x74:
    mask = 0x4000;
    break;
  case 0x70:
    mask = 0x00E0;
    break;
  case 0x72:
    mask = 0xE000;
    break;
  case 0x78:
    mask = 0xFF00;
    break;
  case 0x7C:
    mask = 0x40FF;
    break;
  case 0x80:
    mask = 0xFF77;
    break;
  case 0x82:
    mask = 0x770F;
    break;
  case 0x84:
    if (!p->chip.enable) {
      for (unsigned i = 0; i < 17; ++i)
        p->registers[i] = 0;
      p->registers[17] &= 0xFF00;
    }
    p->registers[slot] = p->status;
    return;
  case 0x88:
    mask = 0xC3FE;
    break;
  default:
    break;
  }
  p->registers[slot] = v & mask;
}
static void bus_byte_write(DbaaPsg *p, unsigned a, uint8_t v) {
  unsigned slot = (a - 0x60) / 2;
  uint16_t old = p->registers[slot];
  if ((a >= 0x62 && a <= 0x65) || (a >= 0x68 && a <= 0x69) ||
      (a >= 0x6C && a <= 0x6D) || (a >= 0x72 && a <= 0x75) ||
      (a >= 0x78 && a <= 0x79) || (a >= 0x7C && a <= 0x7D))
    flush_samples(p, p->cycles);
  switch (a) {
  case 0x62:
  case 0x68:
    byte_write(p, a, v);
    p->registers[slot] = (old & 0xFF00) | (v & 0xC0);
    return;
  case 0x63:
  case 0x69:
    byte_write(p, a, v);
    p->registers[slot] = (old & 0x00C0) | ((uint16_t)v << 8);
    return;
  case 0x64:
  case 0x6C:
  case 0x72:
  case 0x74:
  case 0x78:
    byte_write(p, a, v);
    return;
  case 0x65:
  case 0x6D:
  case 0x75:
    byte_write(p, a, v);
    p->registers[slot] = (uint16_t)(v & 0x40) << 8;
    return;
  case 0x73:
    byte_write(p, a, v);
    p->registers[slot] = (uint16_t)(v & 0xE0) << 8;
    return;
  case 0x79:
    byte_write(p, a, v);
    p->registers[slot] = (uint16_t)v << 8;
    return;
  case 0x7C:
    byte_write(p, a, v);
    p->registers[slot] = (old & 0x4000) | v;
    return;
  case 0x7D:
    byte_write(p, a, v);
    p->registers[slot] = (old & 0x00FF) | ((uint16_t)(v & 0x40) << 8);
    return;
  default:
    break;
  }
  if ((a & ~1u) == 0x84)
    old = p->status;
  unsigned shift = 8 * (a & 1);
  half_write(p, a & ~1u,
             (uint16_t)((old & ~(255u << shift)) | ((uint16_t)v << shift)));
}
int Dbaa_PsgWrite(DbaaPsg *p, uint64_t cycles, uint32_t address, uint32_t value,
                  unsigned width) {
  if ((width != 1 && width != 2 && width != 4) || address < 0x04000060 ||
      address > 0x040000A0u - width || (address & (width - 1)) ||
      !Dbaa_PsgAdvance(p, cycles))
    return 0;
  unsigned a = address - 0x04000000;
  if (width == 1)
    bus_byte_write(p, a, (uint8_t)value);
  else if (width == 2)
    half_write(p, a, (uint16_t)value);
  else if (a >= 0x90)
    word_write(p, a, value);
  else {
    half_write(p, a, (uint16_t)value);
    half_write(p, a + 2, (uint16_t)(value >> 16));
  }
  return 1;
}
uint8_t Dbaa_PsgStatus(const DbaaPsg *p) { return p ? p->status : 0; }
void Dbaa_PsgSample(DbaaPsg *p, int16_t *left, int16_t *right) {
  if (p)
    GBAudioSamplePSG(&p->chip, left, right);
  else
    *left = *right = 0;
}
