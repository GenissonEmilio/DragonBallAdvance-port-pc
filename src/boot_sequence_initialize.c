#include "sequences.h"
/* USA 0x080F3368: 136 complete bytes match the ROM. */
void BootSequence_Initialize(void **vram, struct DbaaSequenceData *sequence,
                             DbaaU32 *counter) {
  struct DbaaTask *task;
  struct DbaaBootSequenceData *data;
  DbaaU16 zero;
  gSystemFlags &= 0xFEFFFFFF;
  task = Task_Create(BootSequence_Run, 44, 0x200, 0x10, BootSequence_OnDestroy);
  data = (struct DbaaBootSequenceData *)SEQUENCE_DATA(task);
  /* Keep the source address live before storing the halfword zero. */
  {
    DbaaU16 *source = &zero;
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, data, 0x01000016);
  }
  data->sequence = sequence;
  data->counter = counter;
  data->vram = vram;
  data->script = gBootSequenceScript;
  sequence->state++;
}
