#include "post_boot.h"
/* USA 0x080EFAA4: 144 complete bytes match the ROM. */
void PostBoot_Initialize(void **vram, struct DbaaSequenceData *sequence,
                         DbaaU32 *counter) {
  struct DbaaTask *task;
  struct DbaaPostBootData *data;
  DbaaU16 zero;
  gSystemFlags &= 0xFEFFFFFF;
  task = Task_Create(PostBoot_Run, 0x1EC, 0x200, 0x10, PostBoot_OnDestroy);
  data = (struct DbaaPostBootData *)SEQUENCE_DATA(task);
  {
    DbaaU16 *source = &zero;
    /* Keep the zero-cell address before its store and BIOS call. */
    __asm__("" : : "r"(source));
    *source = 0;
    Bios_CpuSet(source, data, 0x010000F6);
  }
  data->sequence = sequence;
  data->counter = counter;
  data->vram = vram;
  sequence->state++;
  {
    register const struct DbaaPostBootBackground **backgrounds __asm__("r4") =
        &data->backgrounds;
    /* Retain the final field address in r4; the template is empty. */
    __asm__("" : "+r"(backgrounds));
    *backgrounds = gPostBootBackgrounds;
  }
}
