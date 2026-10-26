#ifndef DBAA_SEQUENCES_H
#define DBAA_SEQUENCES_H

#include "graphics.h"
#include "input.h"
#include "runtime.h"
#include "tasks.h"

/* Partial ARM views recovered from the matched sequence/fade routines. */
struct DbaaSequenceData {
  DbaaU8 state, firstStep, nextStep, completionMode;
  DbaaU16 sequenceId, unknown06;
  DbaaU32 counter;
  void *vram;
  DbaaTaskCallback onComplete;
};
struct DbaaSequenceContext {
  DbaaU8 unknown00[8];
  DbaaU32 flags;
  DbaaU8 unknown0C[10], skipRequested;
};
struct DbaaSequenceClearRects {
  DbaaU8 data[4][4];
};
extern struct DbaaSequenceContext gSequenceContext;
extern const DbaaU8 gSequenceClearFlags[];
extern DbaaU8 gBgClearValues[4];
extern struct DbaaSequenceClearRects gBgClearRects;
typedef void (*DbaaSequenceInitializer)(void **vram,
                                        struct DbaaSequenceData *data,
                                        DbaaU32 *counter);
extern const DbaaSequenceInitializer gSequenceInitializers[];
extern const DbaaTaskCallback gSequenceCompletionCallbacks[];
void Sequence_Prepare(void);
void Sequence_Run(void);
void Sequence_Finish(void);
void Sequence_OnDestroy(struct DbaaTask *task);
struct DbaaFadeData {
  DbaaS16 step, value, target;
  DbaaU8 flags, bgMask, delay, unknown09[3];
};
extern struct DbaaTask *gScreenFadeTask;
struct DbaaFadeData *Func_0800C0C8(int mode);
void ScreenFade_Commit(void);
void ScreenFade_Run(void);
void ScreenFade_OnDestroy(struct DbaaTask *task);
void Tasks_DestroyPriorityRange(DbaaU16 lower, DbaaU16 upper);
void Sequence_StartAfterBoot(void);
struct DbaaBootScreen {
  DbaaU16 backgroundId;
  DbaaU8 background, palette;
  DbaaU16 scrollX, scrollY;
  DbaaU8 fadeInFrames, fadeOutFrames;
  DbaaU16 holdFrames;
  DbaaU8 pauseFrames, unknown0D[3];
};
struct DbaaBootSequenceData {
  DbaaU8 state, unknown01[3];
  struct DbaaSequenceData *sequence;
  DbaaU32 *counter;
  void **vram;
  int flags;
  DbaaU8 unknown14[4];
  DbaaS16 timer;
  DbaaU16 unknown1A;
  void (*phase)(struct DbaaBootSequenceData *);
  DbaaU16 duration, unknown22;
  const struct DbaaBootScreen *script;
  DbaaU8 screen, unknown29[3];
};
extern const struct DbaaBootScreen gBootSequenceScript[];
void BootSequence_Initialize(void **vram, struct DbaaSequenceData *sequence,
                             DbaaU32 *counter);
void BootSequence_Run(void);
void BootSequence_Finish(void);
void BootSequence_Update(void);
void BootSequence_StartScreen(struct DbaaBootSequenceData *data);
void BootSequence_FadeIn(struct DbaaBootSequenceData *data);
void BootSequence_BeginHold(struct DbaaBootSequenceData *data);
void BootSequence_Hold(struct DbaaBootSequenceData *data);
void BootSequence_BeginFadeOut(struct DbaaBootSequenceData *data);
void BootSequence_FadeOut(struct DbaaBootSequenceData *data);
void BootSequence_BeginPause(struct DbaaBootSequenceData *data);
void BootSequence_Advance(struct DbaaBootSequenceData *data);
void BootSequence_ClearScreen(DbaaU8 screen);
void BootSequence_LoadScreen(DbaaU8 screen);
void Func_0810AEEC(void);
struct DbaaBootBackground {
  DbaaU8 width, unknown01, height, unknown03[5];
  const void *tiles;
  DbaaU8 unknown0C[4];
  const void *palette;
  DbaaU16 unknown14, paletteHalfwords;
  const DbaaU16 *tilemap;
};
extern const struct DbaaBootBackground *gBootBackgrounds[];
void Bios_LZ77UnCompVram(const void *source, void *destination);
void Func_08114668(const void *palette, DbaaU8 offset, DbaaU32 count);
void Graphics_LoadBgPalette(const void *palette, DbaaU8 offset, DbaaU32 count);
void BootSequence_OnDestroy(struct DbaaTask *task);
void Task_Destroy(struct DbaaTask *task);

#define SEQUENCE_DATA(task_)                                                   \
  ((task_)->flags & 0x10                                                       \
       ? (struct DbaaSequenceData *)(0x02000000 + (task_)->dataOffset * 4)     \
       : (struct DbaaSequenceData *)(0x03000000 + (task_)->dataOffset))
#define RESOLVED_TASK_DATA(task_, type_)                                       \
  ({                                                                           \
    type_ *p;                                                                  \
    if ((task_)->flags & 0x10)                                                 \
      p = (void *)(0x02000000 + (task_)->dataOffset * 4);                      \
    else                                                                       \
      p = (void *)(0x03000000 + (task_)->dataOffset);                          \
    p;                                                                         \
  })

#endif
