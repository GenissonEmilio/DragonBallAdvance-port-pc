#ifndef DBAA_SPRITES_H
#define DBAA_SPRITES_H
#include "backgrounds.h"
/* Shared 48-byte ARM sprite layout, first recovered in the post-boot tasks. */
struct DbaaPostBootSprite {
  void *vram;
  DbaaU32 frameIndex;
  DbaaU32 flags;
  DbaaU16 animation, animationCursor;
  DbaaS16 x, y;
  DbaaU16 order;
  DbaaS16 animationDelay;
  DbaaU16 previousAnimation;
  DbaaU8 variant, previousVariant, speed, oamStart, subframes, palette;
  DbaaU8 unknown20[16];
};

struct DbaaOamEntry {
  DbaaU16 attr0, attr1, attr2;
  DbaaS8 next;
  DbaaU8 unknown07;
};
struct DbaaVramTransfer {
  DbaaU32 source, destination;
  DbaaU16 size, unknown0A;
};
extern DbaaS8 gOamOrderHeads[], gOamOrderTails[];
extern DbaaU8 gOamFreeIndex, gVramQueueWriteIndex;
extern struct DbaaOamEntry gOamAllocatedEntries[];
extern struct DbaaVramTransfer gVramTransferQueue[];
extern void *gTaskHeapLimit;
struct DbaaOamEntry *Graphics_AllocateOam(DbaaU8 order);
void Graphics_DrawSprite(struct DbaaPostBootSprite *sprite);
typedef int (*DbaaAnimationCommand)(const int *, struct DbaaPostBootSprite *);
extern DbaaAnimationCommand const gAnimationCommands[12];
int Sprite_UpdateAnimation(struct DbaaPostBootSprite *sprite);
int SpriteCommand_Tiles(const int *command, struct DbaaPostBootSprite *sprite);
int SpriteCommand_Palette(const int *command,
                          struct DbaaPostBootSprite *sprite);
int SpriteCommand_JumpBack(const int *command,
                           struct DbaaPostBootSprite *sprite);
int SpriteCommand_End(const int *command, struct DbaaPostBootSprite *sprite);
int SpriteCommand_Sound(const int *command, struct DbaaPostBootSprite *sprite);
int SpriteCommand_Hitbox(const int *command, struct DbaaPostBootSprite *sprite);
int SpriteCommand_Translate(const int *command,
                            struct DbaaPostBootSprite *sprite);
int SpriteCommand_Skip(const int *command, struct DbaaPostBootSprite *sprite);
int SpriteCommand_Switch(const int *command, struct DbaaPostBootSprite *sprite);
int SpriteCommand_Reserved9(const int *command,
                            struct DbaaPostBootSprite *sprite);
int SpriteCommand_Priority(const int *command,
                           struct DbaaPostBootSprite *sprite);
int SpriteCommand_Order(const int *command, struct DbaaPostBootSprite *sprite);
#endif
