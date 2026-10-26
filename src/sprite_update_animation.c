/* USA 0x0810FD70: 244 complete bytes match the ROM. */
#include "sprites.h"
/* Empty constraints preserve the two original script-lookup register lifetimes.
 */
#define ANIMATION_SCRIPT(sprite)                                               \
  ({                                                                           \
    register const struct DbaaSpriteTables *tables __asm__("r1") =             \
        gSpriteTables;                                                         \
    register DbaaU32 animation __asm__("r0");                                  \
    register const int *const *const *animations __asm__("r1");                \
    register const int *const *variants __asm__("r1");                         \
    __asm__("" : "+r"(tables));                                                \
    animation = sprite->animation;                                             \
    __asm__("" : "+r"(animation));                                             \
    animations = tables->animations;                                           \
    __asm__("" : "+r"(animations));                                            \
    variants = animations[animation];                                          \
    __asm__("" : "+r"(variants));                                              \
    variants[sprite->variant];                                                 \
  })
int Sprite_UpdateAnimation(struct DbaaPostBootSprite *sprite) {
  const int *script, *command;
  if (sprite->previousVariant != sprite->variant ||
      sprite->previousAnimation != sprite->animation) {
    sprite->previousVariant = sprite->variant;
    sprite->previousAnimation = sprite->animation;
    sprite->animationCursor = 0;
    sprite->animationDelay = 0;
    sprite->flags &= ~0x4000;
  }
  if (sprite->flags & 0x4000)
    return 0;
  if (sprite->animationDelay > 0) {
    sprite->animationDelay -= sprite->speed << 4;
    return 1;
  }
  script = ANIMATION_SCRIPT(sprite);
  command = script + sprite->animationCursor;
  while (*command < 0) {
    int result = gAnimationCommands[~*command](command, sprite);
    if (result != 1) {
      if (result != -1)
        return result;
      {
        register const int *replacement __asm__("r1") =
            ANIMATION_SCRIPT(sprite);
        __asm__("" : "+r"(replacement));
        sprite->animationCursor = 0;
        script = replacement;
      }
    }
    command = script + sprite->animationCursor;
  }
  sprite->animationDelay =
      (*command << 8) + sprite->animationDelay - (sprite->speed << 4);
  sprite->frameIndex = command[1];
  sprite->flags |= 0x04000000;
  sprite->animationCursor += 2;
  return 1;
}
