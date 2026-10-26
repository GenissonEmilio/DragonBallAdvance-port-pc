/* Readable algorithm reference: NONMATCHING and excluded from production. */
#include "audio.h"
extern const DbaaU8 gCgbVolumeTable[];
#define BYTE(a) (*(volatile DbaaU8 *)(a))
#define WORD(a) (*(volatile DbaaU32 *)(a))
#define FIELD32(p, n) (*(DbaaU32 *)((p) + (n)))
struct CgbChannel {
  DbaaU8 status, type, right, left, attack, decay, sustain, release;
  DbaaU8 key, envelopeVol, envelopeGoal, envelopeCtr, echoVolume, echoLength;
  DbaaU8 unknown0E[11];
  DbaaU8 sustainGoal, nrx4, pan, panMask, cgbStatus, length, sweep;
  DbaaU32 frequency;
  const DbaaU32 *wave, *current;
  DbaaU8 unknown2C[20];
};
typedef char CgbChannelSizeCheck[sizeof(struct CgbChannel) == 64 ? 1 : -1];
void Cgb_Update(void) {
  int channel;
  struct CgbChannel *ch;
  int sweepCounter;
  struct SoundInfo *sound = gSoundInfoPointer;
  volatile DbaaU8 *reg0, *reg1, *reg2, *reg3, *reg4;
  int envelope;
  int mask = 0xFF;
  if (sound->unknown09[1])
    sound->unknown09[1]--;
  else
    sound->unknown09[1] = 14;
  for (channel = 1, ch = sound->cgbChannels; channel <= 4; channel++, ch++) {
    if (!(ch->status & 0xC7))
      continue;
    switch (channel) {
    case 1:
      reg0 = (void *)0x04000060;
      reg1 = (void *)0x04000062;
      reg2 = (void *)0x04000063;
      reg3 = (void *)0x04000064;
      reg4 = (void *)0x04000065;
      break;
    case 2:
      reg0 = (void *)0x04000061;
      reg1 = (void *)0x04000068;
      reg2 = (void *)0x04000069;
      reg3 = (void *)0x0400006C;
      reg4 = (void *)0x0400006D;
      break;
    case 3:
      reg0 = (void *)0x04000070;
      reg1 = (void *)0x04000072;
      reg2 = (void *)0x04000073;
      reg3 = (void *)0x04000074;
      reg4 = (void *)0x04000075;
      break;
    default:
      reg0 = (void *)0x04000071;
      reg1 = (void *)0x04000078;
      reg2 = (void *)0x04000079;
      reg3 = (void *)0x0400007C;
      reg4 = (void *)0x0400007D;
      break;
    }
    sweepCounter = sound->unknown09[1];
    envelope = *reg2;
    if (ch->status & 0x80) {
      if (!(ch->status & 0x40)) {
        ch->status = 3;
        ch->cgbStatus = 3;
        Cgb_UpdateVolume((DbaaU8 *)ch);
        switch (channel) {
        case 1:
          *reg0 = ch->sweep;
        case 2:
          *reg1 = ((int)ch->wave << 6) + ch->length;
          break;
        case 3:
          if (ch->wave != ch->current) {
            *reg0 = 0x40;
            WORD(0x04000090) = ch->wave[0];
            WORD(0x04000094) = ch->wave[1];
            WORD(0x04000098) = ch->wave[2];
            WORD(0x0400009C) = ch->wave[3];
            ch->current = ch->wave;
          }
          *reg0 = 0;
          *reg1 = ch->length;
          if (ch->length)
            ch->nrx4 = 0xC0;
          else
            ch->nrx4 = 0x80;
          goto initialize_envelope;
        default:
          *reg1 = ch->length;
          *reg3 = (int)ch->wave << 3;
          break;
        }
        envelope = ch->attack + 8;
        if (ch->length)
          ch->nrx4 = 0x40;
        else
          ch->nrx4 = 0;
      initialize_envelope:
        ch->envelopeCtr = ch->attack;
        if (!(DbaaS8)(ch->attack & mask))
          goto attack_complete;
        ch->envelopeVol = 0;
        goto decrement_envelope;
      } else
        goto stop_channel;
    } else if (ch->status & 4) {
      ch->echoLength--;
      if ((DbaaS8)(ch->echoLength & mask) > 0)
        goto write_hardware;
    stop_channel:
      Cgb_Stop(channel);
      ch->status = 0;
      goto clear_flags;
    } else if ((ch->status & 0x40) && (ch->status & 3)) {
      ch->status = 0xFC & ch->status;
      ch->envelopeCtr = ch->release;
      if (!(DbaaS8)(ch->release & mask))
        goto start_echo;
      ch->cgbStatus = 1 | ch->cgbStatus;
      if (channel != 3)
        envelope = ch->release;
      goto decrement_envelope;
    } else {
    process_envelope:
      if (ch->envelopeCtr)
        goto decrement_envelope;
      if (channel == 3)
        ch->cgbStatus = 1 | ch->cgbStatus;
      Cgb_UpdateVolume((DbaaU8 *)ch);
      if (!(ch->status & 3)) {
        ch->envelopeVol--;
        if ((DbaaS8)(ch->envelopeVol & mask) <= 0) {
        start_echo:
          ch->envelopeVol = (ch->envelopeGoal * ch->echoVolume + 255) >> 8;
          if (!ch->envelopeVol)
            goto stop_channel;
          ch->status = 4 | ch->status;
          ch->cgbStatus = 1 | ch->cgbStatus;
          if (channel != 3)
            envelope = 8;
          goto write_hardware;
        } else
          ch->envelopeCtr = ch->release;
      } else if ((ch->status & 3) == 1) {
      reload_sustain:
        ch->envelopeVol = ch->sustainGoal;
        ch->envelopeCtr = 7;
        goto decrement_envelope;
      } else if ((ch->status & 3) == 2) {
        int current, goal;
        ch->envelopeVol--;
        current = (int)((DbaaU32)(ch->envelopeVol & mask) << 24);
        goal = (int)((DbaaU32)ch->sustainGoal << 24);
        if (current > goal)
          goto reload_decay;
      decay_complete:
        if (!ch->sustain) {
          ch->status = 0xFC & ch->status;
          goto start_echo;
        }
        ch->status--;
        ch->cgbStatus = 1 | ch->cgbStatus;
        if (channel != 3)
          envelope = 8;
        goto reload_sustain;
      reload_decay:
        ch->envelopeCtr = ch->decay;
        goto decrement_envelope;
      } else {
        ch->envelopeVol++;
        if ((DbaaU8)(ch->envelopeVol & mask) < ch->envelopeGoal)
          goto reload_attack;
      attack_complete:
        ch->status--;
        ch->envelopeCtr = ch->decay;
        if (!(DbaaS8)(ch->decay & mask))
          goto decay_complete;
        ch->cgbStatus = 1 | ch->cgbStatus;
        ch->envelopeVol = ch->envelopeGoal;
        if (channel != 3)
          envelope = ch->decay;
        goto decrement_envelope;
      reload_attack:
        ch->envelopeCtr = ch->attack;
        goto decrement_envelope;
      }
    }
  decrement_envelope:
    ch->envelopeCtr--;
    if (!sweepCounter) {
      sweepCounter--;
      goto process_envelope;
    }
  write_hardware:
    if (ch->cgbStatus & 2) {
      if (channel <= 3 && (ch->type & 8)) {
        int bias = BYTE(0x04000089);
        if (bias <= 0x3F)
          ch->frequency = (ch->frequency + 2) & 0x7FC;
        else if (bias <= 0x7F)
          ch->frequency = (ch->frequency + 1) & 0x7FE;
      }
      if (channel != 4)
        *reg3 = ch->frequency;
      else
        *reg3 = (*reg3 & 8) | ch->frequency;
      ch->nrx4 = (ch->nrx4 & 0xC0) + *((DbaaU8 *)&ch->frequency + 1);
      *reg4 = (DbaaS8)(ch->nrx4 & mask);
    }
    if (ch->cgbStatus & 1) {
      BYTE(0x04000081) = (BYTE(0x04000081) & ~ch->panMask) | ch->pan;
      if (channel == 3) {
        *reg2 = gCgbVolumeTable[ch->envelopeVol];
        if (ch->nrx4 & 0x80) {
          *reg0 = 0x80;
          *reg4 = ch->nrx4;
          ch->nrx4 &= 0x7F;
        }
      } else {
        DbaaU32 volumeMask = 15;
        *reg2 = (envelope & volumeMask) + (ch->envelopeVol << 4);
        *reg4 = ch->nrx4 | 0x80;
        if (channel == 1 && !(*reg0 & 8))
          *reg4 = ch->nrx4 | 0x80;
      }
    }
  clear_flags:
    ch->cgbStatus = 0;
  }
}
