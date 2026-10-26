/* USA 0x0810B8EC: 1100 complete bytes match the ROM.
 * GNU C register-flow reconstruction; all instruction selection is performed
 * by the unmodified compiler. Empty constraints emit no instructions.
 * Fifteen C label addresses are non-allocated debugger metadata. The scoped
 * volatile register zero retains the original dead store; its stack home
 * overlaps the earlier scoped callback spill. See reference/cgb_update.c.
 */
#include "audio.h"
/* Numeric data addresses avoid agbcc -O1's unused duplicate .rodata words.
 * The real loads and their literal pools remain in the compared .text. */
#define SOUND_INFO_POINTER_ADDRESS 0x03007FF0
#define CGB_VOLUME_TABLE_ADDRESS 0x08A676C4
#define KEEP(v) __asm__ volatile("" : "+r"(v))
#define SET(v, e)                                                              \
  {                                                                            \
    v = (e);                                                                   \
    KEEP(v);                                                                   \
  }
#define B(a) (*(volatile DbaaU8 *)(a))
#define H(a) (*(volatile DbaaU32 *)(a))
#define C(n) (ch[n])
#define W(n) (*(DbaaU32 *)(ch + (n)))
void Cgb_Update(void) {
  volatile struct {
    int counter;
    struct SoundInfo *sound;
    volatile DbaaU8 *reg0, *reg2, *reg3, *reg4;
  } hw;
  register DbaaU32 a __asm__("r0"), b __asm__("r1"), c __asm__("r2"),
      d __asm__("r3");
  register DbaaU8 *ch __asm__("r4");
  register DbaaU32 zero __asm__("r5");
  register int channel __asm__("r6");
  register DbaaU32 reg1;
  register DbaaU32 envelope __asm__("r8");
  register DbaaU8 *nextCh __asm__("r9");
  register int nextChannel __asm__("r10");
  static void *const anchors[] __attribute__((
      unused, section(".debug_dbaa_flow"))) = {&&initialize_envelope,
                                               &&store_nrx4,
                                               &&wave_ready,
                                               &&wave_empty,
                                               &&echo_length_byte,
                                               &&decay_rate_loaded,
                                               &&release_envelope_loaded,
                                               &&echo_volume_loaded,
                                               &&echo_envelope_selected,
                                               &&decay_envelope_loaded,
                                               &&release_volume_byte,
                                               &&decay_volume_byte,
                                               &&wave_word_stored_0,
                                               &&wave_word_stored_1,
                                               &&wave_word_stored_2};
  {
    a = ((DbaaU32)*(struct SoundInfo **)SOUND_INFO_POINTER_ADDRESS);
  };
  hw.sound = (void *)a;
  {
    a = (((struct SoundInfo *)a)->unknown09[1]);
  };
  if (a) {
    {
      a = (a - 1);
    };
    {
      b = ((DbaaU32)hw.sound);
    };
    ((struct SoundInfo *)b)->unknown09[1] = a;
  } else {
    {
      a = (14);
    };
    {
      c = ((DbaaU32)hw.sound);
    };
    ((struct SoundInfo *)c)->unknown09[1] = a;
  }
  {
    channel = (1);
  };
  {
    a = ((DbaaU32)hw.sound);
  };
  {
    ch = (((struct SoundInfo *)a)->cgbChannels);
  };
/* Select the hardware channel and capture its envelope register. */
next_record:
  {
    b = (C(0));
  };
  {
    a = (0xC7);
  };
  {
    a = (a & b);
  };
  {
    c = (channel + 1);
  };
  {
    nextChannel = (c);
  };
  SET(c, 64);
  {
    c = (c + (DbaaU32)ch);
  };
  {
    nextCh = ((void *)c);
  };
  if (!a)
    goto next_channel;
  switch (channel) {
  case 1: {
    a = (0x04000060);
  };
    hw.reg0 = (void *)a;
    {
      reg1 = (0x04000062);
    };
    {
      c = (0x04000063);
    };
    hw.reg2 = (void *)c;
    {
      a = (a + 4);
    };
    hw.reg3 = (void *)a;
    SET(c, c + 2);
    goto registers_ready;
  case 2: {
    a = (0x04000061);
  };
    hw.reg0 = (void *)a;
    {
      reg1 = (0x04000068);
    };
    {
      c = (0x04000069);
    };
    goto noise_registers;
  case 3: {
    a = (0x04000070);
  };
    hw.reg0 = (void *)a;
    {
      reg1 = (0x04000072);
    };
    {
      c = (0x04000073);
    };
    hw.reg2 = (void *)c;
    {
      a = (a + 4);
    };
    hw.reg3 = (void *)a;
    {
      c = (c + 2);
    };
    goto registers_ready;
  default: {
    a = (0x04000071);
  };
    hw.reg0 = (void *)a;
    {
      reg1 = (0x04000078);
    };
    {
      c = (0x04000079);
    };
  noise_registers:
    hw.reg2 = (void *)c;
    {
      a = (a + 11);
    };
    hw.reg3 = (void *)a;
    {
      c = (c + 4);
    };
  }
registers_ready:
  hw.reg4 = (void *)c;
  {
    a = ((DbaaU32)hw.sound);
  };
  {
    a = (((struct SoundInfo *)a)->unknown09[1]);
  };
  hw.counter = a;
  {
    c = ((DbaaU32)hw.reg2);
  };
  {
    a = (B(c));
  };
  {
    envelope = (a);
  };
  {
    c = (b);
  };
  {
    a = (0x80);
  };
  {
    a = (a & c);
  };
  if (!a)
    goto continuation;
  {
    d = (0x40);
  };
  {
    a = (d);
  };
  {
    a = (a & c);
  };
  {
    a = (a << 24);
  };
  {
    zero = (a >> 24);
  };
  KEEP(channel);
  {
    a = (channel + 1);
  };
  {
    nextChannel = (a);
  };
  SET(b, 64);
  {
    b = (b + (DbaaU32)ch);
  };
  {
    nextCh = ((void *)b);
  };
  if (zero)
    goto stop_channel;
  {
    a = (3);
  };
  C(0) = a;
  C(0x1D) = a;
  {
    volatile DbaaU32 savedMask;
    {
      a = ((DbaaU32)ch);
    };
    savedMask = d;
    Cgb_UpdateVolume((void *)a);
    {
      d = (savedMask);
    };
  }
  switch (channel) {
  case 1: {
    a = (C(0x1F));
  };
    {
      c = ((DbaaU32)hw.reg0);
    };
    B(c) = a;
  case 2: {
    a = (W(0x24));
  };
    SET(a, a << 6);
    {
      b = (C(0x1E));
    };
    {
      a = (b + a);
    };
    B(reg1) = a;
    goto tonal_envelope;
  case 3: {
    b = (W(0x24));
  };
    {
      a = (W(0x28));
    };
    if (b == a)
      goto wave_ready;
    {
      c = ((DbaaU32)hw.reg0);
    };
    B(c) = d;
    {
      b = (0x04000090);
    };
    {
      c = (W(0x24));
    };
    {
      a = (H(c));
    };
    H(b) = a;
  wave_word_stored_0:
    {
      b = (b + 4);
    };
    {
      a = (H(c + 4));
    };
    H(b) = a;
  wave_word_stored_1:
    {
      b = (b + 4);
    };
    {
      a = (H(c + 8));
    };
    H(b) = a;
  wave_word_stored_2:
    {
      b = (b + 4);
    };
    {
      a = (H(c + 12));
    };
    H(b) = a;
    W(0x28) = c;
  /* Wave RAM is refreshed only when the sample pointer changes. */
  wave_ready:
    {
      a = ((DbaaU32)hw.reg0);
    };
    B(a) = zero;
    {
      a = (C(0x1E));
    };
    B(reg1) = a;
    {
      a = (B(ch + 0x1E));
    };
    if (!a)
      goto wave_empty;
    {
      a = (0xC0);
    };
    goto store_nrx4;
  wave_empty:
    {
      b = (-128);
    };
    C(0x1A) = b;
    goto initialize_envelope;
  default: {
    a = (C(0x1E));
  };
    B(reg1) = a;
    {
      a = (W(0x24));
    };
    {
      a = (a << 3);
    };
    {
      c = ((DbaaU32)hw.reg3);
    };
    B(c) = a;
  tonal_envelope:
    {
      a = (C(4));
    };
    {
      a = (a + 8);
    };
    {
      envelope = (a);
    };
    {
      a = (C(0x1E));
    };
    if (a) {
      a = (0x40);
    };
  store_nrx4:
    C(0x1A) = a;
  }
initialize_envelope:
  SET(b, C(4));
  {
    c = (0);
  };
  C(0xB) = b;
  {
    a = (0xFF);
  };
  {
    a = (a & b);
  };
  KEEP(channel);
  SET(b, channel + 1);
  {
    nextChannel = (b);
  };
  SET(b, 64);
  {
    b = (b + (DbaaU32)ch);
  };
  {
    nextCh = ((void *)b);
  };
  if (!a)
    goto attack_complete;
  C(9) = c;
  goto decrement_envelope;
/* Echo, release, sustain, decay and attack preserve byte wrap. */
continuation:
  {
    a = (4);
  };
  {
    a = (a & c);
  };
  if (!a)
    goto release_check;
  {
    a = (C(0xD));
  };
  {
    a = (a - 1);
  };
  C(0xD) = a;
  {
    c = (0xFF);
  };
  {
    a = (a & c);
  };
echo_length_byte:
  {
    a = (a << 24);
  };
  KEEP(channel);
  {
    b = (channel + 1);
  };
  {
    nextChannel = (b);
  };
  SET(c, 64);
  {
    c = (c + (DbaaU32)ch);
  };
  {
    nextCh = ((void *)c);
  };
  if ((int)a > 0)
    goto write_hardware;
stop_channel:
  Cgb_Stop(channel);
  {
    a = (0);
  };
  C(0) = a;
  goto clear_flags;
release_check:
  {
    a = (0x40);
  };
  {
    a = (a & b);
  };
  KEEP(channel);
  {
    c = (channel + 1);
  };
  {
    nextChannel = (c);
  };
  SET(c, 64);
  {
    c = (c + (DbaaU32)ch);
  };
  {
    nextCh = ((void *)c);
  };
  if (!a)
    goto process_envelope;
  {
    a = (3);
  };
  {
    a = (a & b);
  };
  if (!a)
    goto process_envelope;
  {
    a = (0xFC);
  };
  {
    a = (a & b);
  };
  SET(c, 0);
  C(0) = a;
  SET(b, C(7));
  C(0xB) = b;
  {
    a = (0xFF);
  };
  {
    a = (a & b);
  };
  if (!a)
    goto start_echo;
  {
    a = (1);
  };
  {
    b = (C(0x1D));
  };
  {
    a = (a | b);
  };
  C(0x1D) = a;
  if (channel == 3)
    goto decrement_envelope;
  c = B(ch + 7);
release_envelope_loaded:
  SET(envelope, c);
  goto decrement_envelope;
process_envelope:
  {
    a = (C(0xB));
  };
  if (a)
    goto decrement_envelope;
  if (channel == 3) {
    {
      a = (1);
    };
    {
      b = (C(0x1D));
    };
    {
      a = (a | b);
    };
    C(0x1D) = a;
  }
  Cgb_UpdateVolume(ch);
  {
    a = (3);
  };
  {
    c = (C(0));
  };
  {
    a = (a & c);
  };
  if (a)
    goto sustain_check;
  {
    a = (C(9));
  };
  {
    a = (a - 1);
  };
  C(9) = a;
  b = 0xFF;
  a = a & b;
release_volume_byte:
  a = a << 24;
  if ((int)a > 0)
    goto reload_release;
start_echo:
  c = C(0xC);
echo_volume_loaded:
  {
    b = (C(0xA));
  };
  {
    a = (c);
  };
  {
    a = (a * b);
  };
  {
    a = (a + 255);
  };
  {
    a = ((int)a >> 8);
  };
  SET(b, 0);
  C(9) = a;
  {
    a = (a << 24);
  };
  if (!a)
    goto stop_channel;
  {
    a = (4);
  };
  {
    c = (C(0));
  };
  {
    a = (a | c);
  };
  C(0) = a;
  {
    a = (1);
  };
  {
    b = (C(0x1D));
  };
  {
    a = (a | b);
  };
  C(0x1D) = a;
  if (channel == 3)
    goto write_hardware;
  c = 8;
echo_envelope_selected:
  {
    envelope = (c);
  };
  goto write_hardware;
reload_release:
  {
    a = (C(7));
  };
  goto store_counter;
sustain_check:
  if (a != 1)
    goto decay_check;
reload_sustain:
  {
    a = (C(0x19));
  };
  C(9) = a;
  {
    a = (7);
  };
  goto store_counter;
decay_check:
  if (a != 2)
    goto attack_step;
  {
    a = (C(9));
  };
  {
    a = (a - 1);
  };
  C(9) = a;
  b = 0xFF;
  a = a & b;
decay_volume_byte:
  a = a << 24;
  {
    c = (C(0x19));
  };
  {
    b = (c << 24);
  };
  if ((int)a > (int)b)
    goto reload_decay;
decay_complete:
  {
    a = (C(6));
  };
  if (a)
    goto sustain_start;
  {
    a = (0xFC);
  };
  {
    b = (C(0));
  };
  {
    a = (a & b);
  };
  C(0) = a;
  goto start_echo;
sustain_start:
  {
    a = (C(0));
  };
  {
    a = (a - 1);
  };
  C(0) = a;
  {
    a = (1);
  };
  {
    c = (C(0x1D));
  };
  {
    a = (a | c);
  };
  C(0x1D) = a;
  if (channel == 3)
    goto reload_sustain;
  {
    a = (8);
  };
  {
    envelope = (a);
  };
  goto reload_sustain;
reload_decay:
  {
    a = (C(5));
  };
  goto store_counter;
attack_step:
  {
    a = (C(9));
  };
  {
    a = (a + 1);
  };
  C(9) = a;
  {
    b = (0xFF);
  };
  {
    a = (a & b);
  };
  {
    c = (C(0xA));
  };
  if (a < c)
    goto reload_attack;
attack_complete:
  {
    a = (C(0));
  };
  {
    a = (a - 1);
  };
  {
    register volatile DbaaU32 decayZero __asm__("r2");
    decayZero = 0;
  }
  C(0) = a;
  {
    b = (C(5));
  };
  C(0xB) = b;
decay_rate_loaded:
  {
    a = (0xFF);
  };
  {
    a = (a & b);
  };
  if (!a)
    goto decay_complete;
  {
    a = (1);
  };
  {
    b = (C(0x1D));
  };
  {
    a = (a | b);
  };
  C(0x1D) = a;
  {
    a = (C(0xA));
  };
  C(9) = a;
  if (channel == 3)
    goto decrement_envelope;
  c = B(ch + 5);
decay_envelope_loaded:
  {
    envelope = (c);
  };
  goto decrement_envelope;
reload_attack:
  {
    a = (C(4));
  };
store_counter:
  C(0xB) = a;
decrement_envelope:
  {
    a = (C(0xB));
  };
  {
    a = (a - 1);
  };
  C(0xB) = a;
  {
    a = (hw.counter);
  };
  if (a)
    goto write_hardware;
  {
    a = (a - 1);
  };
  hw.counter = a;
  goto process_envelope;
/* Pitch rounding follows the hardware PWM setting. */
write_hardware:
  {
    a = (2);
  };
  {
    b = (C(0x1D));
  };
  {
    a = (a & b);
  };
  if (!a)
    goto volume_hardware;
  if (channel > 3)
    goto write_frequency;
  {
    a = (8);
  };
  {
    c = (C(1));
  };
  {
    a = (a & c);
  };
  if (!a)
    goto write_frequency;
  {
    a = (0x04000089);
  };
  {
    a = (B(a));
  };
  if ((int)a > 0x3F)
    goto bias_high;
  {
    a = (W(0x20));
  };
  {
    a = (a + 2);
  };
  {
    b = (0x7FC);
  };
  goto round_frequency;
bias_high:
  if ((int)a > 0x7F)
    goto write_frequency;
  {
    a = (W(0x20));
  };
  {
    a = (a + 1);
  };
  {
    b = (0x7FE);
  };
round_frequency:
  {
    a = (a & b);
  };
  W(0x20) = a;
write_frequency:
  if (channel == 4)
    goto noise_frequency;
  {
    a = (W(0x20));
  };
  {
    b = ((DbaaU32)hw.reg3);
  };
  B(b) = a;
  goto high_frequency;
noise_frequency:
  {
    c = ((DbaaU32)hw.reg3);
  };
  {
    a = (B(c));
  };
  {
    b = (8);
  };
  {
    b = (b & a);
  };
  {
    a = (W(0x20));
  };
  {
    a = (a | b);
  };
  B(c) = a;
high_frequency:
  {
    a = (0xC0);
  };
  {
    b = (C(0x1A));
  };
  {
    a = (a & b);
  };
  {
    b = ((DbaaU32)ch);
  };
  {
    b = (b + 0x21);
  };
  {
    b = (B(b));
  };
  {
    a = (b + a);
  };
  C(0x1A) = a;
  {
    c = (0xFF);
  };
  {
    a = (a & c);
  };
  {
    b = ((DbaaU32)hw.reg4);
  };
  B(b) = a;
/* Route the channel and update its hardware envelope/trigger. */
volume_hardware:
  {
    a = (1);
  };
  {
    c = (C(0x1D));
  };
  {
    a = (a & c);
  };
  if (!a)
    goto clear_flags;
  {
    b = (0x04000081);
  };
  {
    a = (B(b));
  };
  {
    c = (C(0x1C));
  };
  {
    a = (a & ~c);
  };
  {
    c = (C(0x1B));
  };
  {
    a = (a | c);
  };
  B(b) = a;
  if (channel != 3)
    goto tonal_volume;
  {
    a = ((DbaaU32)CGB_VOLUME_TABLE_ADDRESS);
    KEEP(a);
  };
  {
    b = (C(9));
  };
  {
    a = (b + a);
  };
  {
    a = (B(a));
  };
  {
    c = ((DbaaU32)hw.reg2);
  };
  B(c) = a;
  {
    b = (0x80);
  };
  SET(a, b);
  {
    c = (C(0x1A));
  };
  {
    a = (a & c);
  };
  if (!a)
    goto clear_flags;
  {
    a = ((DbaaU32)hw.reg0);
  };
  B(a) = b;
  {
    a = (C(0x1A));
  };
  {
    b = ((DbaaU32)hw.reg4);
  };
  B(b) = a;
  {
    a = (0x7F);
  };
  {
    c = (C(0x1A));
  };
  {
    a = (a & c);
  };
  C(0x1A) = a;
  goto clear_flags;
tonal_volume:
  {
    a = (15);
  };
  {
    b = (envelope);
  };
  {
    b = (b & a);
  };
  {
    envelope = (b);
  };
  {
    c = (C(9));
  };
  {
    a = (c << 4);
  };
  {
    a = (a + envelope);
  };
  {
    b = ((DbaaU32)hw.reg2);
  };
  B(b) = a;
  {
    c = (0x80);
  };
  {
    a = (C(0x1A));
  };
  {
    a = (a | c);
  };
  {
    b = ((DbaaU32)hw.reg4);
  };
  B(b) = a;
  if (channel != 1)
    goto clear_flags;
  {
    a = ((DbaaU32)hw.reg0);
  };
  {
    b = (B(a));
  };
  {
    a = (8);
  };
  {
    a = (a & b);
  };
  if (a)
    goto clear_flags;
  {
    a = (C(0x1A));
  };
  {
    a = (a | c);
  };
  {
    b = ((DbaaU32)hw.reg4);
  };
  B(b) = a;
clear_flags:
  {
    a = (0);
  };
  C(0x1D) = a;
next_channel:
  {
    channel = (nextChannel);
  };
  {
    ch = (nextCh);
  };
  if (channel <= 4)
    goto next_record;
}
