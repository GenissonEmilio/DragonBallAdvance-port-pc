/* NONMATCHING GBA C probe. The semantic implementation is shared with the
 * native port. asm/sound_main.s owns the exact mixed Thumb/ARM ROM image. */
typedef unsigned int uint32_t;
typedef int int32_t;
typedef unsigned char uint8_t;
#define DBAA_MIXER_ARGUMENTS void
#define Dbaa_SoundMain Func_0810A084
#define R8(a) (*(volatile uint8_t *)(a))
#define R32(a) (*(volatile uint32_t *)(a))
#define W8(a, v) (*(volatile uint8_t *)(a) = (v))
#define W32(a, v) (*(volatile uint32_t *)(a) = (v))
#define CALL(t, a, b, c)                                                       \
  ((void (*)(uint32_t, uint32_t, uint32_t))(t))((a), (b), (c))
#include "../port/include/pcm_mixer_impl.h"
