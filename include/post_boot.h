#ifndef DBAA_POST_BOOT_H
#define DBAA_POST_BOOT_H

#include "sequences.h"
#include "initialization.h"
#include "audio.h"
#include "task_memory.h"
#include "sprites.h"

/* Partial ARM layouts recovered from sequence 0x4D. */
struct DbaaPostBootSpriteConfig {
  DbaaU16 animation, variant;
  DbaaU8 tiles, palette, unknown06[2];
};
struct DbaaPostBootBackground {
  DbaaU8 background, priority;
  DbaaS16 backgroundId;
  DbaaU8 sourcePalette, destinationPalette, paletteCount, flip;
  DbaaU16 scrollX, scrollY;
};
struct DbaaPostBootCurtainData {
  struct DbaaPostBootSprite *sprite0, *sprite1;
  DbaaU8 background, unknown09;
  DbaaS16 x, y, velocityX, velocityY;
  DbaaU8 unknown12[2];
  struct DbaaPostBootData *parent;
};
struct DbaaPostBootScrollData {
  DbaaU8 index, slot, background, unknown03;
  struct DbaaPostBootData *parent;
  const struct DbaaPostBootBackground *entry;
  DbaaS16 elapsed, duration, initialX, targetX;
  int position, velocity, acceleration;
};
struct DbaaPostBootRingData {
  DbaaU8 unknown00[4];
  DbaaU32 elapsed;
  DbaaU16 step, unknown0A;
  int (*phase)(struct DbaaPostBootRingData *);
  struct DbaaPostBootSprite *sprites;
  DbaaU32 unknown14;
  int angle, angularVelocity, angularAcceleration;
  int radius, radialVelocity, radialAcceleration;
  struct DbaaPostBootData *parent;
};
struct DbaaPostBootFadeData {
  DbaaU16 control, alpha;
  DbaaU8 start, target;
  DbaaS16 increment, current, elapsed, duration;
  DbaaU8 unknown0E[2];
  struct DbaaPostBootData *parent;
};
struct DbaaPostBootData {
  DbaaU8 state, unknown01[3];
  struct DbaaSequenceData *sequence;
  DbaaU32 *counter;
  void **vram;
  DbaaU32 flags, elapsed;
  DbaaU16 step;
  DbaaS16 tileChunk;
  void (*phase)(struct DbaaPostBootData *);
  struct DbaaPostBootSprite sprites[9];
  const struct DbaaPostBootBackground *backgrounds;
  struct DbaaPostBootFadeData *fade;
  struct DbaaTask *child0;
  struct DbaaTask *scrollTasks[2];
  struct DbaaTask *child3, *skipTask;
};
extern const struct DbaaPostBootBackground gPostBootBackgrounds[];
extern const DbaaU16 gPostBootDefaultBackground;
extern const struct DbaaPostBootSpriteConfig gPostBootSpriteConfig[];
extern const DbaaU16 gPostBootTimeline[];
extern struct MusicPlayer *gPostBootMusicPlayer;
extern DbaaU16 gVramHeapMap[];
extern const DbaaU8 gPostBootTileRuns[9][4];
extern const DbaaU8 gPostBootMapRows[10];
extern const DbaaU8 gPostBootBlueLevels[8];
extern const DbaaS16 gPostBootScrollRanges[][2];
extern const DbaaS16 gSineTable[];

void PostBoot_Initialize(void **vram, struct DbaaSequenceData *sequence,
                         DbaaU32 *counter);
void PostBoot_OnDestroy(struct DbaaTask *task);
void PostBoot_Run(void);
void PostBoot_Update(void);
void PostBoot_Finish(void);
void PostBoot_PrepareSprites(struct DbaaPostBootData *data);
void PostBoot_FreeSprites(struct DbaaPostBootData *data);
void PostBoot_Begin(struct DbaaPostBootData *data);
void PostBoot_EnableBackgrounds(struct DbaaPostBootData *data);
void PostBoot_DisableBackgrounds(struct DbaaPostBootData *data);
void PostBoot_Phase3(struct DbaaPostBootData *data);
void PostBoot_Phase4(struct DbaaPostBootData *data);
void PostBoot_Phase5(struct DbaaPostBootData *data);
void PostBoot_Phase6(struct DbaaPostBootData *data);
void PostBoot_Phase7(struct DbaaPostBootData *data);
void PostBoot_Phase8(struct DbaaPostBootData *data);
void PostBoot_Phase9(struct DbaaPostBootData *data);
void PostBoot_Phase10(struct DbaaPostBootData *data);
void PostBoot_Phase11(struct DbaaPostBootData *data);
void PostBoot_Phase12(struct DbaaPostBootData *data);
void PostBoot_Phase13(struct DbaaPostBootData *data);
void PostBoot_Phase14(struct DbaaPostBootData *data);
void PostBoot_Phase15(struct DbaaPostBootData *data);
void PostBoot_Phase16(struct DbaaPostBootData *data);
void PostBoot_Phase17(struct DbaaPostBootData *data);
void PostBoot_Phase18(struct DbaaPostBootData *data);
void PostBoot_Phase19(struct DbaaPostBootData *data);
void PostBoot_CopyTileChunk(struct DbaaPostBootData *data);
void PostBoot_Phase21(struct DbaaPostBootData *data);
void PostBoot_Phase22(struct DbaaPostBootData *data);
void PostBoot_Phase23(struct DbaaPostBootData *data);
void PostBoot_Phase24(struct DbaaPostBootData *data);
void PostBoot_Phase25(struct DbaaPostBootData *data);
void PostBoot_Phase26(struct DbaaPostBootData *data);
void PostBoot_Phase27(struct DbaaPostBootData *data);
void PostBoot_Phase28(struct DbaaPostBootData *data);
void PostBoot_Phase29(struct DbaaPostBootData *data);
void PostBoot_Phase30(struct DbaaPostBootData *data);
void PostBoot_Phase31(struct DbaaPostBootData *data);
void PostBoot_Phase32(struct DbaaPostBootData *data);
void PostBoot_Phase33(struct DbaaPostBootData *data);
void PostBoot_Phase34(struct DbaaPostBootData *data);
void PostBoot_Phase35(struct DbaaPostBootData *data);
void PostBoot_Phase36(struct DbaaPostBootData *data);
void PostBoot_Phase37(struct DbaaPostBootData *data);
void PostBoot_Phase38(struct DbaaPostBootData *data);
void PostBoot_Phase39(struct DbaaPostBootData *data);
void PostBoot_Phase40(struct DbaaPostBootData *data);
void PostBoot_Phase41(struct DbaaPostBootData *data);
void PostBoot_Phase42(struct DbaaPostBootData *data);
void PostBoot_Phase43(struct DbaaPostBootData *data);
void PostBoot_Phase44(struct DbaaPostBootData *data);
void PostBoot_Phase45(struct DbaaPostBootData *data);
void PostBoot_Phase46(struct DbaaPostBootData *data);
void PostBoot_Phase47(struct DbaaPostBootData *data);
void PostBoot_Phase48(struct DbaaPostBootData *data);
struct DbaaTask *PostBoot_CreateRing(struct DbaaPostBootData *parent);
void PostBoot_RingOnDestroy(struct DbaaTask *task);
void PostBoot_RingRun(void);
int PostBoot_RingBegin(struct DbaaPostBootRingData *data);
int PostBoot_RingInitContract(struct DbaaPostBootRingData *data);
int PostBoot_RingContract(struct DbaaPostBootRingData *data);
int PostBoot_RingHold(struct DbaaPostBootRingData *data);
int PostBoot_RingInitSpin(struct DbaaPostBootRingData *data);
int PostBoot_RingSpin(struct DbaaPostBootRingData *data);
int PostBoot_RingRelease(struct DbaaPostBootRingData *data);
int PostBoot_RingTail(struct DbaaPostBootRingData *data);
void PostBoot_RingStep(struct DbaaPostBootRingData *data);
void PostBoot_RingDraw(struct DbaaPostBootRingData *data);
void PostBoot_PositionRing(struct DbaaPostBootRingData *data, int angle, DbaaU16 radius);
struct DbaaTask *PostBoot_CreateScroll(struct DbaaPostBootData *parent, DbaaU8 index,
                                     DbaaU8 slot, DbaaU16 duration);
void PostBoot_ScrollRun(void);
void PostBoot_ScrollOnDestroy(struct DbaaTask *task);
struct DbaaTask *PostBoot_CreateCurtain(struct DbaaPostBootData *parent);
void PostBoot_CurtainOnDestroy(struct DbaaTask *task);
void PostBoot_CurtainWait(void);
void PostBoot_CurtainMove(void);
void PostBoot_CurtainHold(void);

void PostBoot_LoadMap(DbaaU8 index);
void PostBoot_LoadPalette(DbaaU8 index);
void PostBoot_ApplyBackground(DbaaU8 index);
void PostBoot_ClearBackgroundMap(DbaaU8 background);
int PostBoot_StartFade(struct DbaaPostBootData *parent, DbaaU8 direction);
struct DbaaPostBootFadeData *PostBoot_CreateFade(struct DbaaPostBootData *parent,
                                              const struct DbaaPostBootFadeData *config);
void PostBoot_FadeRun(void);
void PostBoot_FadeOnDestroy(struct DbaaTask *task);
void *Runtime_Memset(void *destination, int value, DbaaU32 size);
void PostBoot_LoadBackground(DbaaU8 index);
void PostBoot_LoadSpecialBackground(DbaaU8 index);
void PostBoot_LoadSpecialTiles(DbaaU8 charBase);
void PostBoot_LoadSpecialMap(DbaaU8 screenBase, DbaaU8 palette);
void PostBoot_LoadSpecialPalette(DbaaU8 palette);
void PostBoot_LoadTiles(DbaaU8 index);
struct DbaaTask *PostBoot_CreateSkipTask(struct DbaaPostBootData *data);
struct DbaaPostBootSkipData {
  DbaaU8 unknown00[8];
  DbaaU16 elapsed, duration;
  struct DbaaPostBootData *parent;
};
void PostBoot_SkipRun(void);
void PostBoot_SkipFade(void);
void PostBoot_SkipOnDestroy(struct DbaaTask *task);
void *Vram_AllocateTiles(DbaaU32 tiles);
void Vram_FreeTiles(void *vram);
int Func_0810FD70(struct DbaaPostBootSprite *sprite);

#endif
