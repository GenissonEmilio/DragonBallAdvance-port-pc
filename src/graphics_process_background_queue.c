/*
 * Graphics_ProcessBackgroundQueue -- exact USA ROM range 0810DDCC..0810E900.
 * GNU C register-flow reconstruction, compiled with agbcc -O1
 * -mthumb-interwork. This is not a claim to have recovered the historical
 * source spelling.
 *
 * Every machine instruction comes from C. All asm templates are empty.
 * flowAnchors contains C label addresses in .debug_dbaa_flow; the linker
 * classifies it as non-allocated INFO metadata. Retaining these basic-block
 * boundaries avoids combine/reload changes without inflating branch lengths.
 * No instruction templates, embedded opcodes, or edits to compiler output.
 *
 * stack[] mirrors the original 68-byte frame. Registers r6/r9/r10 carry the
 * background descriptor, vertical progress, and horizontal progress in the
 * metatile paths; other register roles change between the text/affine paths.
 * The readable algorithm reference is reference/graphics_background_queue.c.
 * See docs/background_queue_matching.md for scope and reproduction commands.
 */
#include "backgrounds.h"
int Graphics_ProcessBackgroundQueue(void) {
  volatile DbaaU32 stack[17];
  static void *const flowAnchors[]
      __attribute__((unused, section(".debug_dbaa_flow"))) = {
          &&anchor_0, &&anchor_1, &&anchor_2, &&anchor_3, &&anchor_4,
          &&anchor_5, &&anchor_6, &&anchor_7, &&anchor_8};

  register DbaaU32 r0 __asm__("r0");
  register DbaaU32 r1 __asm__("r1");
  register DbaaU32 r2 __asm__("r2");
  register DbaaU32 r3 __asm__("r3");
  register DbaaU32 r4 __asm__("r4");
  register DbaaU32 r5 __asm__("r5");
  register DbaaU32 r6 __asm__("r6");
  register DbaaU32 r7;
  register DbaaU32 r8 __asm__("r8");
  register DbaaU32 r9 __asm__("r9");
  register DbaaU32 r10 __asm__("r10");
  register DbaaU32 r12 __asm__("r12");
  r0 = 0x0u;                     /* 0810DDD8 */
  stack[1] = r0;                 /* 0810DDDA */
  r0 = 0x3003f74u;               /* 0810DDDC */
  r1 = 0x3003d00u;               /* 0810DDDE */
  r2 = *(volatile DbaaU8 *)(r0); /* 0810DDE0 */
  r3 = r0 + 0x0u;                /* 0810DDE2 */
  r4 = r1 + 0x0u;                /* 0810DDE4 */
  __asm__ volatile("" : : "r"(r1));
  r1 = *(volatile DbaaU8 *)(r4); /* 0810DDE6 */
  __asm__ volatile("" : : "r"(r4));
  if (r2 != r1)
    goto L_0810DDF0; /* 0810DDEA */
  goto L_0810E8DE;   /* 0810DDEC */
/* Check VBlank before consuming the next queued descriptor. */
L_0810DDF0:
  r0 = 0x4000004u;                /* 0810DDF0 */
  r1 = *(volatile DbaaU16 *)(r0); /* 0810DDF2 */
  r0 = 0x1u;                      /* 0810DDF4 */
  r0 = r0 & r1;                   /* 0810DDF6 */
  if (r0 != 0x0u)
    goto L_0810DE10; /* 0810DDFA */
  r0 = 0x0u;         /* 0810DDFC */
  goto L_0810E8E0;   /* 0810DDFE */
L_0810DE10:
  r0 = 0x4000006u;                /* 0810DE10 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810DE12 */
  r2 = 0x3002b60u;                /* 0810DE14 */
  r1 = *(volatile DbaaU8 *)(r3);  /* 0810DE16 */
  __asm__ volatile("" : : "r"(r3));
  r0 = r1 << 0x2u;                /* 0810DE18 */
  r0 = r0 + r2;                   /* 0810DE1A */
  r6 = *(volatile DbaaU32 *)(r0); /* 0810DE1C */
  r1 = r1 + 0x1u;                 /* 0810DE1E */
  r0 = 0xfu;                      /* 0810DE20 */
  r1 = r1 & r0;                   /* 0810DE22 */
  *(volatile DbaaU8 *)(r3) = r1;  /* 0810DE24 */
  r2 = *(DbaaU16 *)(r6 + 0x2eu);  /* 0810DE26 */
  r0 = 0x20u;                     /* 0810DE28 */
  r0 = r0 & r2;                   /* 0810DE2A */
  if (r0 == 0x0u)
    goto L_0810DE3C;             /* 0810DE2E */
  r1 = *(DbaaU32 *)(r6 + 0x30u); /* 0810DE30 */
  r0 = *(DbaaU32 *)(r6 + 0x34u); /* 0810DE32 */
  if (r1 != r0)
    goto L_0810DE3C; /* 0810DE36 */
  goto L_0810E8D2;   /* 0810DE38 */
/* Derive text/affine entry size and VRAM map pitch. */
L_0810DE3C:
  r3 = *(DbaaU16 *)(r6 + 0x14u); /* 0810DE3C */
  stack[0] = r3;                 /* 0810DE3E */
  r3 = 0x3u;                     /* 0810DE40 */
  r4 = r3 + 0x0u;                /* 0810DE42 */
  r4 = r4 & r2;                  /* 0810DE44 */
  r7 = stack[0];                 /* 0810DE46 */
  if (r4 <= 0x1u)
    goto L_0810DE80;              /* 0810DE4A */
  r0 = 0x3003c00u;                /* 0810DE4C */
  r1 = *(volatile DbaaU16 *)(r0); /* 0810DE4E */
  r0 = r3 + 0x0u;                 /* 0810DE50 */
  r0 = r0 & r1;                   /* 0810DE52 */
  __asm__ volatile("" : : "r"(r1));
  if (r0 == 0x0u)
    goto L_0810DE80;              /* 0810DE56 */
  r1 = 0x3003120u;                /* 0810DE58 */
  r0 = r4 << 0x1u;                /* 0810DE5A */
  r0 = r0 + r1;                   /* 0810DE5C */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810DE5E */
  __asm__ volatile("" : : "r"(r1));
  r3 = r0 >> 0xeu;  /* 0810DE60 */
  r0 = 0x80u;       /* 0810DE62 */
  r0 = r0 << 0xdu;  /* 0810DE64 */
  r0 = r0 << r3;    /* 0810DE66 */
  r0 = r0 >> 0x10u; /* 0810DE68 */
  stack[3] = r0;    /* 0810DE6A */
  r0 = 0x1u;        /* 0810DE6C */
  goto L_0810DE9E;  /* 0810DE6E */
L_0810DE80:
  r1 = 0x20u;      /* 0810DE80 */
  stack[3] = r1;   /* 0810DE82 */
  r0 = 0x3003120u; /* 0810DE84 */
  r1 = r4 << 0x1u; /* 0810DE86 */
  r1 = r1 + r0;    /* 0810DE88 */
  __asm__ volatile("" : : "r"(r0));
  r0 = *(volatile DbaaU16 *)(r1); /* 0810DE8A */
  r3 = r0 >> 0xeu;                /* 0810DE8C */
  __asm__ volatile("" : : "r"(r0));
  if (r3 == 0x1u)
    goto L_0810DE96; /* 0810DE90 */
  if (r3 != 0x3u)
    goto L_0810DE9C; /* 0810DE94 */
L_0810DE96:
  r2 = 0x80u;      /* 0810DE96 */
  r2 = r2 << 0x4u; /* 0810DE98 */
  stack[1] = r2;   /* 0810DE9A */
L_0810DE9C:
  r0 = 0x2u; /* 0810DE9C */
L_0810DE9E:
  stack[2] = r0;                 /* 0810DE9E */
  r1 = stack[3];                 /* 0810DEA0 */
  r2 = stack[2];                 /* 0810DEA2 */
  r0 = r1 + 0x0u;                /* 0810DEA4 */
  r0 = r0 * r2;                  /* 0810DEA6 */
  r0 = r0 << 0x10u;              /* 0810DEA8 */
  r0 = r0 >> 0x10u;              /* 0810DEAA */
  stack[3] = r0;                 /* 0810DEAC */
  r2 = *(DbaaU16 *)(r6 + 0x2eu); /* 0810DEAE */
  r0 = 0x20u;                    /* 0810DEB0 */
  r9 = r0;                       /* 0810DEB2 */
  r0 = r0 & r2;                  /* 0810DEB4 */
  if (r0 == 0x0u)
    goto L_0810DEBC; /* 0810DEB8 */
  goto L_0810E29C;   /* 0810DEBA */
L_0810DEBC:
  r0 = 0x40u;   /* 0810DEBC */
  r0 = r0 & r2; /* 0810DEBE */
  if (r0 == 0x0u)
    goto L_0810DEC6; /* 0810DEC2 */
  goto L_0810E18C;   /* 0810DEC4 */
/* Unscrolled maps: flip-aware CPU copies or contiguous DMA rows. */
L_0810DEC6:
  r0 = *(DbaaU16 *)(r6 + 0x24u); /* 0810DEC6 */
  r1 = stack[3];                 /* 0810DEC8 */
  r0 = r0 * r1;                  /* 0810DECA */
  r1 = *(DbaaU32 *)(r6 + 0xcu);  /* 0810DECC */
  r1 = r1 + r0;                  /* 0810DECE */
  r4 = *(DbaaU16 *)(r6 + 0x22u); /* 0810DED0 */
  r8 = r4;                       /* 0810DED2 */
  __asm__ volatile("" : : "r"(r4));
  r4 = stack[2];                 /* 0810DED4 */
  r0 = r8;                       /* 0810DED6 */
  r0 = r0 * r4;                  /* 0810DED8 */
  r4 = r1 + r0;                  /* 0810DEDA */
  r5 = *(DbaaU16 *)(r6 + 0x28u); /* 0810DEDC */
  r1 = 0x80u;                    /* 0810DEDE */
  r1 = r1 << 0x1u;               /* 0810DEE0 */
  r0 = r1 + 0x0u;                /* 0810DEE2 */
  __asm__ volatile("" : : "r"(r1));
  r0 = r0 & r2; /* 0810DEE4 */
  if (r0 != 0x0u)
    goto L_0810DEEC; /* 0810DEE8 */
  goto L_0810DFF8;   /* 0810DEEA */
L_0810DEEC:
  r0 = 0x80u;   /* 0810DEEC */
  r0 = r0 & r2; /* 0810DEEE */
  if (r0 == 0x0u)
    goto L_0810DF7C;             /* 0810DEF2 */
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810DEF4 */
  r0 = r0 + r5;                  /* 0810DEF6 */
  r0 = r0 - 0x1u;                /* 0810DEF8 */
  r0 = r0 * r7;                  /* 0810DEFA */
  r2 = stack[2];                 /* 0810DEFC */
  r0 = r0 * r2;                  /* 0810DEFE */
  r2 = *(DbaaU32 *)(r6 + 0x10u); /* 0810DF00 */
  r2 = r2 + r0;                  /* 0810DF02 */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810DF04 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810DF06 */
  r0 = r0 + r1;                  /* 0810DF08 */
  r0 = r0 - 0x1u;                /* 0810DF0A */
  r3 = stack[2];                 /* 0810DF0C */
  r0 = r0 * r3;                  /* 0810DF0E */
  r2 = r2 + r0;                  /* 0810DF10 */
  r0 = r5 - 0x1u;                /* 0810DF12 */
  r0 = r0 << 0x10u;              /* 0810DF14 */
  r5 = r0 >> 0x10u;              /* 0810DF16 */
  r7 = 0xffffu;                  /* 0810DF18 */
  if (r5 != r7)
    goto L_0810DF22; /* 0810DF1C */
  goto L_0810E8C2;   /* 0810DF1E */
L_0810DF22:
  r1 = stack[0];  /* 0810DF22 */
  r0 = r1 + 0x0u; /* 0810DF24 */
  r0 = r0 * r3;   /* 0810DF26 */
  r8 = r0;        /* 0810DF28 */
  r3 = r7 + 0x0u; /* 0810DF2A */
  r10 = r3;       /* 0810DF2C */
  __asm__ volatile("" : : "r"(r0), "r"(r3));
L_0810DF2E:
  r3 = 0x0u;                     /* 0810DF2E */
  r7 = r5 - 0x1u;                /* 0810DF30 */
  r0 = stack[3];                 /* 0810DF32 */
  r5 = r4 + r0;                  /* 0810DF34 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810DF36 */
  if (r3 >= r1)
    goto L_0810DF60; /* 0810DF3A */
  r0 = 0xc0u;        /* 0810DF3C */
  r0 = r0 << 0x4u;   /* 0810DF3E */
  r9 = r0;           /* 0810DF40 */
L_0810DF42:
  r0 = r3 << 0x1u;                /* 0810DF42 */
  r1 = r0 + r4;                   /* 0810DF44 */
  r12 = r1;                       /* 0810DF46 */
  r0 = r2 - r0;                   /* 0810DF48 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810DF4A */
  r1 = r9;                        /* 0810DF4C */
  r0 = r0 ^ r1;                   /* 0810DF4E */
  r1 = r12;                       /* 0810DF50 */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810DF52 */
  r0 = r3 + 0x1u;                 /* 0810DF54 */
  r0 = r0 << 0x10u;               /* 0810DF56 */
  r3 = r0 >> 0x10u;               /* 0810DF58 */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810DF5A */
  if (r3 < r0)
    goto L_0810DF42; /* 0810DF5E */
L_0810DF60:
  r4 = r5 + 0x0u;   /* 0810DF60 */
  r1 = r8;          /* 0810DF62 */
  r2 = r2 - r1;     /* 0810DF64 */
  r0 = r7 << 0x10u; /* 0810DF66 */
  r5 = r0 >> 0x10u; /* 0810DF68 */
  if (r5 != r10)
    goto L_0810DF2E; /* 0810DF6C */
  goto L_0810E8C2;   /* 0810DF6E */
L_0810DF7C:
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810DF7C */
  r0 = r0 * r7;                  /* 0810DF7E */
  r2 = stack[2];                 /* 0810DF80 */
  r0 = r0 * r2;                  /* 0810DF82 */
  r2 = *(DbaaU32 *)(r6 + 0x10u); /* 0810DF84 */
  r2 = r2 + r0;                  /* 0810DF86 */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810DF88 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810DF8A */
  r0 = r0 + r1;                  /* 0810DF8C */
  r0 = r0 - 0x1u;                /* 0810DF8E */
  r3 = stack[2];                 /* 0810DF90 */
  r0 = r0 * r3;                  /* 0810DF92 */
  r2 = r2 + r0;                  /* 0810DF94 */
  r0 = r5 - 0x1u;                /* 0810DF96 */
  r0 = r0 << 0x10u;              /* 0810DF98 */
  r5 = r0 >> 0x10u;              /* 0810DF9A */
  r7 = 0xffffu;                  /* 0810DF9C */
  if (r5 != r7)
    goto L_0810DFA6; /* 0810DFA0 */
  goto L_0810E8C2;   /* 0810DFA2 */
L_0810DFA6:
  r1 = stack[0];  /* 0810DFA6 */
  r0 = r1 + 0x0u; /* 0810DFA8 */
  r0 = r0 * r3;   /* 0810DFAA */
  r8 = r0;        /* 0810DFAC */
  r3 = r7 + 0x0u; /* 0810DFAE */
  r10 = r3;       /* 0810DFB0 */
  __asm__ volatile("" : : "r"(r0), "r"(r3));
L_0810DFB2:
  r3 = 0x0u;                     /* 0810DFB2 */
  r7 = r5 - 0x1u;                /* 0810DFB4 */
  r0 = stack[3];                 /* 0810DFB6 */
  r5 = r4 + r0;                  /* 0810DFB8 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810DFBA */
  if (r3 >= r1)
    goto L_0810DFE4; /* 0810DFBE */
  r0 = 0x80u;        /* 0810DFC0 */
  r0 = r0 << 0x3u;   /* 0810DFC2 */
  r9 = r0;           /* 0810DFC4 */
L_0810DFC6:
  r0 = r3 << 0x1u;                /* 0810DFC6 */
  r1 = r0 + r4;                   /* 0810DFC8 */
  r12 = r1;                       /* 0810DFCA */
  r0 = r2 - r0;                   /* 0810DFCC */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810DFCE */
  r1 = r9;                        /* 0810DFD0 */
  r0 = r0 ^ r1;                   /* 0810DFD2 */
  r1 = r12;                       /* 0810DFD4 */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810DFD6 */
  r0 = r3 + 0x1u;                 /* 0810DFD8 */
  r0 = r0 << 0x10u;               /* 0810DFDA */
  r3 = r0 >> 0x10u;               /* 0810DFDC */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810DFDE */
  if (r3 < r0)
    goto L_0810DFC6; /* 0810DFE2 */
L_0810DFE4:
  r4 = r5 + 0x0u;   /* 0810DFE4 */
  r2 = r2 + r8;     /* 0810DFE6 */
  r0 = r7 << 0x10u; /* 0810DFE8 */
  r5 = r0 >> 0x10u; /* 0810DFEA */
  if (r5 != r10)
    goto L_0810DFB2; /* 0810DFEE */
  goto L_0810E8C2;   /* 0810DFF0 */
L_0810DFF8:
  r0 = 0x80u;   /* 0810DFF8 */
  r0 = r0 & r2; /* 0810DFFA */
  if (r0 == 0x0u)
    goto L_0810E07C;             /* 0810DFFE */
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E000 */
  r0 = r0 + r5;                  /* 0810E002 */
  r0 = r0 - 0x1u;                /* 0810E004 */
  r0 = r0 * r7;                  /* 0810E006 */
  r1 = stack[2];                 /* 0810E008 */
  r0 = r0 * r1;                  /* 0810E00A */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E00C */
  r1 = r1 + r0;                  /* 0810E00E */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E010 */
  r2 = stack[2];                 /* 0810E012 */
  r0 = r0 * r2;                  /* 0810E014 */
  r2 = r1 + r0;                  /* 0810E016 */
  r0 = r5 - 0x1u;                /* 0810E018 */
  r0 = r0 << 0x10u;              /* 0810E01A */
  r5 = r0 >> 0x10u;              /* 0810E01C */
  r3 = 0xffffu;                  /* 0810E01E */
  if (r5 != r3)
    goto L_0810E028; /* 0810E022 */
  goto L_0810E8C2;   /* 0810E024 */
L_0810E028:
  r0 = stack[0];  /* 0810E028 */
  r1 = stack[2];  /* 0810E02A */
  r7 = r0 + 0x0u; /* 0810E02C */
  r7 = r7 * r1;   /* 0810E02E */
  r8 = r7;        /* 0810E030 */
  r10 = r3;       /* 0810E032 */
L_0810E034:
  r3 = 0x0u;                     /* 0810E034 */
  r7 = r5 - 0x1u;                /* 0810E036 */
  r0 = stack[3];                 /* 0810E038 */
  r5 = r4 + r0;                  /* 0810E03A */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E03C */
  if (r3 >= r1)
    goto L_0810E066; /* 0810E040 */
  r0 = 0x80u;        /* 0810E042 */
  r0 = r0 << 0x4u;   /* 0810E044 */
  r9 = r0;           /* 0810E046 */
L_0810E048:
  r0 = r3 << 0x1u;                /* 0810E048 */
  r1 = r0 + r4;                   /* 0810E04A */
  r12 = r1;                       /* 0810E04C */
  r0 = r0 + r2;                   /* 0810E04E */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E050 */
  r1 = r9;                        /* 0810E052 */
  r0 = r0 ^ r1;                   /* 0810E054 */
  r1 = r12;                       /* 0810E056 */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E058 */
  r0 = r3 + 0x1u;                 /* 0810E05A */
  r0 = r0 << 0x10u;               /* 0810E05C */
  r3 = r0 >> 0x10u;               /* 0810E05E */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810E060 */
  if (r3 < r0)
    goto L_0810E048; /* 0810E064 */
L_0810E066:
  r4 = r5 + 0x0u;   /* 0810E066 */
  r1 = r8;          /* 0810E068 */
  r2 = r2 - r1;     /* 0810E06A */
  r0 = r7 << 0x10u; /* 0810E06C */
  r5 = r0 >> 0x10u; /* 0810E06E */
  if (r5 != r10)
    goto L_0810E034; /* 0810E072 */
  goto L_0810E8C2;   /* 0810E074 */
L_0810E07C:
  r0 = 0x1u;    /* 0810E07C */
  r3 = r3 & r0; /* 0810E07E */
  if (r3 == 0x0u)
    goto L_0810E128; /* 0810E082 */
  r2 = stack[2];     /* 0810E084 */
  if (r2 != 0x2u)
    goto L_0810E128; /* 0810E088 */
  r3 = r9;           /* 0810E08A */
  r0 = r8;           /* 0810E08C */
  __asm__ volatile("" : : "r"(r8));
  r3 = r3 - r0; /* 0810E08E */
  r9 = r3;      /* 0810E090 */
  if ((int)r3 <= (int)0x0u)
    goto L_0810E128;             /* 0810E094 */
  r0 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E096 */
  r0 = r0 + r8;                  /* 0810E098 */
  r3 = r0 + 0x0u;                /* 0810E09A */
  __asm__ volatile("" : : "r"(r0));
  r3 = r3 - 0x20u; /* 0810E09C */
  if ((int)r3 <= (int)0x0u)
    goto L_0810E128;             /* 0810E0A0 */
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E0A2 */
  r0 = r0 * r7;                  /* 0810E0A4 */
  r0 = r0 << 0x1u;               /* 0810E0A6 */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E0A8 */
  r1 = r1 + r0;                  /* 0810E0AA */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E0AC */
  r0 = r0 << 0x1u;               /* 0810E0AE */
  r2 = r1 + r0;                  /* 0810E0B0 */
  r1 = r9;                       /* 0810E0B2 */
  __asm__ volatile("" : : "r"(r9));
  r1 = r1 << 0x1u;  /* 0810E0B4 */
  r9 = r1;          /* 0810E0B6 */
  r3 = r3 << 0x1u;  /* 0810E0B8 */
  r0 = r5 - 0x1u;   /* 0810E0BA */
  r0 = r0 << 0x10u; /* 0810E0BC */
  r5 = r0 >> 0x10u; /* 0810E0BE */
  r7 = 0xffffu;     /* 0810E0C0 */
  if (r5 != r7)
    goto L_0810E0CA; /* 0810E0C4 */
  goto L_0810E8C2;   /* 0810E0C6 */
L_0810E0CA:
  r1 = 0x40000d4u; /* 0810E0CA */
  r0 = r9;         /* 0810E0CC */
  __asm__ volatile("" : : "r"(r9));
  r0 = (int)r0 >> 0x1u; /* 0810E0CE */
  r8 = r0;              /* 0810E0D0 */
  r0 = 0x80u;           /* 0810E0D2 */
  r0 = r0 << 0x18u;     /* 0810E0D4 */
  r7 = r8;              /* 0810E0D6 */
  r7 = r7 | r0;         /* 0810E0D8 */
  r8 = r7;              /* 0810E0DA */
  r3 = (int)r3 >> 0x1u; /* 0810E0DC */
  r12 = r3;             /* 0810E0DE */
  __asm__ volatile("" : : "r"(r12));
  r3 = r3 | r0; /* 0810E0E0 */
  r12 = r3;     /* 0810E0E2 */
L_0810E0E4:
  *(volatile DbaaU32 *)(r1) = r2;        /* 0810E0E4 */
  *(volatile DbaaU32 *)(r1 + 0x4u) = r4; /* 0810E0E6 */
  r7 = r8;                               /* 0810E0E8 */
  *(volatile DbaaU32 *)(r1 + 0x8u) = r7; /* 0810E0EA */
  r0 = *(volatile DbaaU32 *)(r1 + 0x8u); /* 0810E0EC */
  r3 = r9;                               /* 0810E0EE */
  r0 = r2 + r3;                          /* 0810E0F0 */
  *(volatile DbaaU32 *)(r1) = r0;        /* 0810E0F2 */
  r7 = stack[1];                         /* 0810E0F4 */
  r0 = r4 + r7;                          /* 0810E0F6 */
  *(volatile DbaaU32 *)(r1 + 0x4u) = r0; /* 0810E0F8 */
  r0 = r12;                              /* 0810E0FA */
  *(volatile DbaaU32 *)(r1 + 0x8u) = r0; /* 0810E0FC */
  r0 = *(volatile DbaaU32 *)(r1 + 0x8u); /* 0810E0FE */
  r3 = stack[3];                         /* 0810E100 */
  r4 = r4 + r3;                          /* 0810E102 */
  r0 = stack[0];                         /* 0810E104 */
  r3 = stack[2];                         /* 0810E106 */
  r7 = r0 + 0x0u;                        /* 0810E108 */
  r7 = r7 * r3;                          /* 0810E10A */
  r10 = r7;                              /* 0810E10C */
  r2 = r2 + r10;                         /* 0810E10E */
  r0 = r5 - 0x1u;                        /* 0810E110 */
  r0 = r0 << 0x10u;                      /* 0810E112 */
  r5 = r0 >> 0x10u;                      /* 0810E114 */
  r7 = 0xffffu;                          /* 0810E116 */
  if (r5 != r7)
    goto L_0810E0E4; /* 0810E11A */
  goto L_0810E8C2;   /* 0810E11C */
L_0810E128:
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E128 */
  r0 = r0 * r7;                  /* 0810E12A */
  r1 = stack[2];                 /* 0810E12C */
  r0 = r0 * r1;                  /* 0810E12E */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E130 */
  r1 = r1 + r0;                  /* 0810E132 */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E134 */
  r2 = stack[2];                 /* 0810E136 */
  r0 = r0 * r2;                  /* 0810E138 */
  r2 = r1 + r0;                  /* 0810E13A */
  r0 = r5 - 0x1u;                /* 0810E13C */
  r0 = r0 << 0x10u;              /* 0810E13E */
  r5 = r0 >> 0x10u;              /* 0810E140 */
  r3 = 0xffffu;                  /* 0810E142 */
  if (r5 != r3)
    goto L_0810E14A; /* 0810E146 */
  goto L_0810E8C2;   /* 0810E148 */
L_0810E14A:
  r1 = 0x40000d4u;  /* 0810E14A */
  r7 = 0x80u;       /* 0810E14C */
  r7 = r7 << 0x18u; /* 0810E14E */
  r8 = r7;          /* 0810E150 */
  __asm__ volatile("" : : "r"(r7));
  r9 = r3;        /* 0810E152 */
  r0 = stack[0];  /* 0810E154 */
  r7 = stack[2];  /* 0810E156 */
  r3 = r0 + 0x0u; /* 0810E158 */
  r3 = r3 * r7;   /* 0810E15A */
L_0810E15C:
  *(volatile DbaaU32 *)(r1) = r2;        /* 0810E15C */
  *(volatile DbaaU32 *)(r1 + 0x4u) = r4; /* 0810E15E */
  r0 = *(DbaaU16 *)(r6 + 0x26u);         /* 0810E160 */
  r7 = stack[2];                         /* 0810E162 */
  r0 = r0 * r7;                          /* 0810E164 */
  r0 = (int)r0 >> 0x1u;                  /* 0810E166 */
  r7 = r8;                               /* 0810E168 */
  r0 = r0 | r7;                          /* 0810E16A */
  *(volatile DbaaU32 *)(r1 + 0x8u) = r0; /* 0810E16C */
  r0 = *(volatile DbaaU32 *)(r1 + 0x8u); /* 0810E16E */
  r0 = stack[3];                         /* 0810E170 */
  r4 = r4 + r0;                          /* 0810E172 */
  r2 = r2 + r3;                          /* 0810E174 */
  r0 = r5 - 0x1u;                        /* 0810E176 */
  r0 = r0 << 0x10u;                      /* 0810E178 */
  r5 = r0 >> 0x10u;                      /* 0810E17A */
  if (r5 != r9)
    goto L_0810E15C; /* 0810E17E */
  goto L_0810E8C2;   /* 0810E180 */
/* Unscrolled metatiles: divide coordinates and copy each clipped chunk. */
L_0810E18C:
  r1 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E18C */
  stack[4] = r1;                 /* 0810E18E */
  r2 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E190 */
  stack[5] = r2;                 /* 0810E192 */
  r3 = 0x0u;                     /* 0810E194 */
  r10 = r3;                      /* 0810E196 */
  __asm__ volatile("" : : "r"(r3));
  r4 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E198 */
  if ((int)r10 < (int)r4)
    goto L_0810E1A0; /* 0810E19C */
  goto L_0810E8C2;   /* 0810E19E */
L_0810E1A0:
  r4 = stack[4];                            /* 0810E1A0 */
  r4 = r4 + r10;                            /* 0810E1A2 */
  r1 = *(DbaaU16 *)(r6 + 0x14u);            /* 0810E1A4 */
  r0 = r4 + 0x0u;                           /* 0810E1A6 */
  r0 = (DbaaU32)Bios_Div((int)r0, (int)r1); /* 0810E1A8 */
  stack[6] = r0;                            /* 0810E1AC */
  r1 = *(DbaaU16 *)(r6 + 0x14u);            /* 0810E1AE */
  r7 = r0 + 0x0u;                           /* 0810E1B0 */
anchor_0:;
  r0 = r7 + 0x0u;                         /* 0810E1B2 */
  r0 = r0 * r1;                           /* 0810E1B4 */
  r4 = r4 - r0;                           /* 0810E1B6 */
  stack[7] = r4;                          /* 0810E1B8 */
  r0 = *(volatile DbaaU16 *)(r6 + 0x28u); /* 0810E1BA */
  r8 = r0;                                /* 0810E1BC */
  r0 = *(DbaaU16 *)(r6 + 0x26u);          /* 0810E1BE */
  r2 = r10;                               /* 0810E1C0 */
  r0 = r0 - r2;                           /* 0810E1C2 */
  r1 = r1 - r4;                           /* 0810E1C4 */
  if ((int)r1 <= (int)r0)
    goto L_0810E1CC; /* 0810E1C8 */
  r1 = r0 + 0x0u;    /* 0810E1CA */
L_0810E1CC:
  r4 = stack[2];  /* 0810E1CC */
  r3 = r1 + 0x0u; /* 0810E1CE */
  r3 = r3 * r4;   /* 0810E1D0 */
  stack[8] = r3;  /* 0810E1D2 */
  r7 = 0x0u;      /* 0810E1D4 */
  __asm__ volatile("" : "+r"(r7) : "r"(r2));
  r9 = r7;        /* 0810E1D6 */
  r1 = r1 + r10;  /* 0810E1D8 */
  stack[14] = r1; /* 0810E1DA */
  if ((int)r9 >= (int)r8)
    goto L_0810E28C; /* 0810E1DE */
L_0810E1E0:
  r4 = stack[5];                            /* 0810E1E0 */
  r4 = r4 + r9;                             /* 0810E1E2 */
  r1 = *(DbaaU16 *)(r6 + 0x16u);            /* 0810E1E4 */
  r0 = r4 + 0x0u;                           /* 0810E1E6 */
  r0 = (DbaaU32)Bios_Div((int)r0, (int)r1); /* 0810E1E8 */
  r3 = *(DbaaU16 *)(r6 + 0x16u);            /* 0810E1EC */
  r1 = r0 + 0x0u;                           /* 0810E1EE */
  r1 = r1 * r3;                             /* 0810E1F0 */
  r4 = r4 - r1;                             /* 0810E1F2 */
  r5 = r3 - r4;                             /* 0810E1F4 */
  r1 = *(DbaaU16 *)(r6 + 0x3cu);            /* 0810E1F6 */
  r1 = r1 << 0x1u;                          /* 0810E1F8 */
  r1 = r1 * r0;                             /* 0810E1FA */
  r0 = stack[6];                            /* 0810E1FC */
  r2 = r0 << 0x1u;                          /* 0810E1FE */
  r0 = *(DbaaU32 *)(r6 + 0x38u);            /* 0810E200 */
  r0 = r0 + r1;                             /* 0810E202 */
  r0 = r0 + r2;                             /* 0810E204 */
  r0 = *(volatile DbaaU16 *)(r0);           /* 0810E206 */
  r2 = *(DbaaU16 *)(r6 + 0x14u);            /* 0810E208 */
anchor_1:;
  r0 = r0 * r2;   /* 0810E20A */
  r1 = r0 + 0x0u; /* 0810E20C */
anchor_2:;
  r1 = r1 * r3;                  /* 0810E20E */
  r0 = r4 + 0x0u;                /* 0810E210 */
  r0 = r0 * r2;                  /* 0810E212 */
  r2 = stack[7];                 /* 0810E214 */
  r0 = r0 + r2;                  /* 0810E216 */
  r1 = r1 + r0;                  /* 0810E218 */
  r3 = stack[2];                 /* 0810E21A */
  r1 = r1 * r3;                  /* 0810E21C */
  r0 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E21E */
  r0 = r0 + r1;                  /* 0810E220 */
  stack[16] = r0;                /* 0810E222 */
  r1 = *(DbaaU16 *)(r6 + 0x24u); /* 0810E224 */
  r0 = *(DbaaU32 *)(r6 + 0xcu);  /* 0810E226 */
  r0 = r0 + r1;                  /* 0810E228 */
  r4 = stack[3];                 /* 0810E22A */
  r1 = r9;                       /* 0810E22C */
  r1 = r1 * r4;                  /* 0810E22E */
  r0 = r0 + r1;                  /* 0810E230 */
  r7 = *(DbaaU16 *)(r6 + 0x22u); /* 0810E232 */
  r0 = r0 + r7;                  /* 0810E234 */
  r1 = r10;                      /* 0810E236 */
  r1 = r1 * r3;                  /* 0810E238 */
  r3 = r0 + r1;                  /* 0810E23A */
  r9 = r9 + r5;                  /* 0810E23C */
  if ((int)r5 <= (int)r8)
    goto L_0810E244; /* 0810E240 */
  r5 = r8;           /* 0810E242 */
L_0810E244:
  r0 = r8;        /* 0810E244 */
  r0 = r0 - r5;   /* 0810E246 */
  r8 = r0;        /* 0810E248 */
  r0 = r5 + 0x0u; /* 0810E24A */
  r5 = r5 - 0x1u; /* 0810E24C */
  if (r0 == 0x0u)
    goto L_0810E286;    /* 0810E250 */
  r2 = 0x40000d4u;      /* 0810E252 */
  r1 = stack[8];        /* 0810E254 */
  r0 = r1 >> 0x1fu;     /* 0810E256 */
  r0 = r1 + r0;         /* 0810E258 */
  r1 = (int)r0 >> 0x1u; /* 0810E25A */
  r0 = 0x80u;           /* 0810E25C */
  r0 = r0 << 0x18u;     /* 0810E25E */
  r1 = r1 | r0;         /* 0810E260 */
  r7 = stack[0];        /* 0810E262 */
  r0 = stack[2];        /* 0810E264 */
  r4 = r7 + 0x0u;       /* 0810E266 */
  r4 = r4 * r0;         /* 0810E268 */
  r12 = r4;             /* 0810E26A */
L_0810E26C:
  r4 = stack[16];                        /* 0810E26C */
  *(volatile DbaaU32 *)(r2) = r4;        /* 0810E26E */
  *(volatile DbaaU32 *)(r2 + 0x4u) = r3; /* 0810E270 */
  *(volatile DbaaU32 *)(r2 + 0x8u) = r1; /* 0810E272 */
  r0 = *(volatile DbaaU32 *)(r2 + 0x8u); /* 0810E274 */
  r7 = stack[3];                         /* 0810E276 */
  r3 = r3 + r7;                          /* 0810E278 */
  r4 = r4 + r12;                         /* 0810E27A */
  stack[16] = r4;                        /* 0810E27C */
  r0 = r5 + 0x0u;                        /* 0810E27E */
  r5 = r5 - 0x1u;                        /* 0810E280 */
  if (r0 != 0x0u)
    goto L_0810E26C; /* 0810E284 */
L_0810E286:
  r0 = *(DbaaU16 *)(r6 + 0x28u); /* 0810E286 */
  if ((int)r9 < (int)r0)
    goto L_0810E1E0; /* 0810E28A */
L_0810E28C:
  r1 = stack[14];                /* 0810E28C */
  r10 = r1;                      /* 0810E28E */
  r2 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E290 */
anchor_3:;
  if ((int)r10 < (int)r2)
    goto L_0810E1A0; /* 0810E294 */
  goto L_0810E8C2;   /* 0810E296 */
/* Scrolling maps: split transfers at the screen-block boundary. */
L_0810E29C:
  r0 = 0x40u;                    /* 0810E29C */
  r0 = r0 & r2;                  /* 0810E29E */
  r3 = *(DbaaU16 *)(r6 + 0x30u); /* 0810E2A0 */
  r1 = 0x3003bf0u;               /* 0810E2A2 */
  r9 = r1;                       /* 0810E2A4 */
  r4 = r4 << 0x2u;               /* 0810E2A6 */
  r8 = r4;                       /* 0810E2A8 */
  if (r0 != 0x0u)
    goto L_0810E2E8;             /* 0810E2AC */
  r2 = r7 + 0x0u;                /* 0810E2AE */
  r0 = r7 << 0x3u;               /* 0810E2B0 */
  r4 = *(DbaaU16 *)(r6 + 0x16u); /* 0810E2B2 */
  r5 = *(DbaaU16 *)(r6 + 0x32u); /* 0810E2B4 */
  if ((int)r3 < (int)r0)
    goto L_0810E2CC; /* 0810E2B8 */
L_0810E2BA:
  r1 = r2 << 0x3u;               /* 0810E2BA */
  r0 = *(DbaaU16 *)(r6 + 0x30u); /* 0810E2BC */
  r0 = r0 - r1;                  /* 0810E2BE */
  *(DbaaU16 *)(r6 + 0x30u) = r0; /* 0810E2C0 */
  r1 = *(DbaaU16 *)(r6 + 0x30u); /* 0810E2C2 */
  r2 = r7 + 0x0u;                /* 0810E2C4 */
  r0 = r7 << 0x3u;               /* 0810E2C6 */
  if ((int)r1 >= (int)r0)
    goto L_0810E2BA; /* 0810E2CA */
L_0810E2CC:
  r2 = r4 + 0x0u;                /* 0810E2CC */
  r0 = r2 << 0x3u;               /* 0810E2CE */
  r3 = *(DbaaU16 *)(r6 + 0x30u); /* 0810E2D0 */
  if ((int)r5 < (int)r0)
    goto L_0810E2E8; /* 0810E2D4 */
L_0810E2D6:
  r1 = r2 << 0x3u;               /* 0810E2D6 */
  r0 = *(DbaaU16 *)(r6 + 0x32u); /* 0810E2D8 */
  r0 = r0 - r1;                  /* 0810E2DA */
  *(DbaaU16 *)(r6 + 0x32u) = r0; /* 0810E2DC */
  r1 = *(DbaaU16 *)(r6 + 0x32u); /* 0810E2DE */
  r2 = r4 + 0x0u;                /* 0810E2E0 */
  r0 = r2 << 0x3u;               /* 0810E2E2 */
  if ((int)r1 >= (int)r0)
    goto L_0810E2D6; /* 0810E2E6 */
L_0810E2E8:
  r0 = r8;                        /* 0810E2E8 */
  r0 = r0 + r9;                   /* 0810E2EA */
  r2 = 0x7u;                      /* 0810E2EC */
  r3 = r3 & r2;                   /* 0810E2EE */
  *(volatile DbaaU16 *)(r0) = r3; /* 0810E2F0 */
  r1 = r9;                        /* 0810E2F2 */
  r1 = r1 + 0x2u;                 /* 0810E2F4 */
  r1 = r1 + r8;                   /* 0810E2F6 */
  r0 = *(DbaaU16 *)(r6 + 0x32u);  /* 0810E2F8 */
  r0 = r0 & r2;                   /* 0810E2FA */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E2FC */
  r0 = *(DbaaU16 *)(r6 + 0x34u);  /* 0810E2FE */
  r4 = *(DbaaU16 *)(r6 + 0x30u);  /* 0810E300 */
  r2 = r4 >> 0x3u;                /* 0810E302 */
  r0 = r0 >> 0x3u;                /* 0810E304 */
  if (r0 != r2)
    goto L_0810E318;             /* 0810E308 */
  r1 = *(DbaaU16 *)(r6 + 0x36u); /* 0810E30A */
  r0 = *(DbaaU16 *)(r6 + 0x32u); /* 0810E30C */
  r1 = r1 >> 0x3u;               /* 0810E30E */
  r0 = r0 >> 0x3u;               /* 0810E310 */
  if (r1 != r0)
    goto L_0810E318; /* 0810E314 */
  goto L_0810E8C2;   /* 0810E316 */
L_0810E318:
  r1 = *(DbaaU16 *)(r6 + 0x2eu); /* 0810E318 */
  r0 = 0x40u;                    /* 0810E31A */
  r0 = r0 & r1;                  /* 0810E31C */
  r3 = r1 + 0x0u;                /* 0810E31E */
  if (r0 == 0x0u)
    goto L_0810E326; /* 0810E322 */
  goto L_0810E7A8;   /* 0810E324 */
L_0810E326:
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E326 */
  r0 = r0 + r2;                  /* 0810E328 */
  r0 = r0 << 0x10u;              /* 0810E32A */
  r0 = r0 >> 0x10u;              /* 0810E32C */
  stack[4] = r0;                 /* 0810E32E */
  r0 = *(DbaaU16 *)(r6 + 0x32u); /* 0810E330 */
  r0 = r0 >> 0x3u;               /* 0810E332 */
  r2 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E334 */
  r0 = r0 + r2;                  /* 0810E336 */
  r0 = r0 << 0x10u;              /* 0810E338 */
  r0 = r0 >> 0x10u;              /* 0810E33A */
  stack[5] = r0;                 /* 0810E33C */
  r0 = *(DbaaU16 *)(r6 + 0x24u); /* 0810E33E */
  __asm__ volatile("" : : "r"(r2));
  r4 = stack[3];                 /* 0810E340 */
  r0 = r0 * r4;                  /* 0810E342 */
  r1 = *(DbaaU32 *)(r6 + 0xcu);  /* 0810E344 */
  r1 = r1 + r0;                  /* 0810E346 */
  r0 = *(DbaaU16 *)(r6 + 0x22u); /* 0810E348 */
  r7 = stack[2];                 /* 0810E34A */
  r0 = r0 * r7;                  /* 0810E34C */
  r4 = r1 + r0;                  /* 0810E34E */
  r0 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E350 */
  r1 = stack[4];                 /* 0810E352 */
  r2 = r1 + r0;                  /* 0810E354 */
  r1 = r2 + 0x1u;                /* 0810E356 */
  r7 = *(DbaaU16 *)(r6 + 0x14u); /* 0810E358 */
  r9 = r0;                       /* 0810E35A */
  if ((int)r1 <= (int)r7)
    goto L_0810E370; /* 0810E35E */
  r0 = r7 - 0x1u;    /* 0810E360 */
  r0 = r2 - r0;      /* 0810E362 */
  r0 = r0 << 0x10u;  /* 0810E364 */
  r0 = r0 >> 0x10u;  /* 0810E366 */
  r8 = r0;           /* 0810E368 */
  goto L_0810E374;   /* 0810E36A */
L_0810E370:
  r2 = 0x0u; /* 0810E370 */
  r8 = r2;   /* 0810E372 */
L_0810E374:
  r0 = *(DbaaU16 *)(r6 + 0x28u); /* 0810E374 */
  r0 = r0 + 0x1u;                /* 0810E376 */
  r0 = r0 << 0x10u;              /* 0810E378 */
  r5 = r0 >> 0x10u;              /* 0810E37A */
  r1 = 0x80u;                    /* 0810E37C */
  r1 = r1 << 0x1u;               /* 0810E37E */
  r0 = r1 + 0x0u;                /* 0810E380 */
  __asm__ volatile("" : : "r"(r1));
  r0 = r0 & r3; /* 0810E382 */
  if (r0 != 0x0u)
    goto L_0810E38A; /* 0810E386 */
  goto L_0810E490;   /* 0810E388 */
L_0810E38A:
  r0 = 0x80u;   /* 0810E38A */
  r0 = r0 & r3; /* 0810E38C */
  if (r0 == 0x0u)
    goto L_0810E414;             /* 0810E390 */
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E392 */
  r0 = r0 + r5;                  /* 0810E394 */
  r0 = r0 - 0x1u;                /* 0810E396 */
  r0 = r0 * r7;                  /* 0810E398 */
  r2 = stack[2];                 /* 0810E39A */
  r0 = r0 * r2;                  /* 0810E39C */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E39E */
  r1 = r1 + r0;                  /* 0810E3A0 */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E3A2 */
  r0 = r0 + r9;                  /* 0810E3A4 */
  r0 = r0 - 0x1u;                /* 0810E3A6 */
  r0 = r0 * r2;                  /* 0810E3A8 */
  r2 = r1 + r0;                  /* 0810E3AA */
  r0 = r5 - 0x1u;                /* 0810E3AC */
  r0 = r0 << 0x10u;              /* 0810E3AE */
  r5 = r0 >> 0x10u;              /* 0810E3B0 */
  r3 = r8;                       /* 0810E3B2 */
  __asm__ volatile("" : : "r"(r3));
  r3 = r3 << 0x10u; /* 0810E3B4 */
  r10 = r3;         /* 0810E3B6 */
  r7 = 0xffffu;     /* 0810E3B8 */
  if (r5 != r7)
    goto L_0810E3C0; /* 0810E3BC */
  goto L_0810E58A;   /* 0810E3BE */
L_0810E3C0:
  r1 = stack[0];  /* 0810E3C0 */
  r3 = stack[2];  /* 0810E3C2 */
  r0 = r1 + 0x0u; /* 0810E3C4 */
  r0 = r0 * r3;   /* 0810E3C6 */
  r8 = r0;        /* 0810E3C8 */
  __asm__ volatile("" : : "r"(r0));
  r12 = r7; /* 0810E3CA */
L_0810E3CC:
  r3 = 0x0u;                     /* 0810E3CC */
  r7 = r5 - 0x1u;                /* 0810E3CE */
  r0 = stack[3];                 /* 0810E3D0 */
  r5 = r4 + r0;                  /* 0810E3D2 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E3D4 */
  if (r3 >= r1)
    goto L_0810E3FE; /* 0810E3D8 */
  r0 = 0xc0u;        /* 0810E3DA */
  r0 = r0 << 0x4u;   /* 0810E3DC */
  r9 = r0;           /* 0810E3DE */
L_0810E3E0:
  r0 = r3 << 0x1u;                /* 0810E3E0 */
  r1 = r0 + r4;                   /* 0810E3E2 */
  stack[15] = r1;                 /* 0810E3E4 */
  r0 = r2 - r0;                   /* 0810E3E6 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E3E8 */
  r1 = r9;                        /* 0810E3EA */
  r0 = r0 ^ r1;                   /* 0810E3EC */
  r1 = stack[15];                 /* 0810E3EE */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E3F0 */
  r0 = r3 + 0x1u;                 /* 0810E3F2 */
  r0 = r0 << 0x10u;               /* 0810E3F4 */
  r3 = r0 >> 0x10u;               /* 0810E3F6 */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810E3F8 */
  if (r3 < r0)
    goto L_0810E3E0; /* 0810E3FC */
L_0810E3FE:
  r4 = r5 + 0x0u; /* 0810E3FE */
  r1 = r8;        /* 0810E400 */
  r2 = r2 - r1;   /* 0810E402 */
  __asm__ volatile("" : : "r"(r1));
  r0 = r7 << 0x10u; /* 0810E404 */
  r5 = r0 >> 0x10u; /* 0810E406 */
  if (r5 != r12)
    goto L_0810E3CC; /* 0810E40A */
  goto L_0810E58A;   /* 0810E40C */
L_0810E414:
  r0 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E414 */
  r0 = r0 * r7;                  /* 0810E416 */
  r2 = stack[2];                 /* 0810E418 */
  r0 = r0 * r2;                  /* 0810E41A */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E41C */
  r1 = r1 + r0;                  /* 0810E41E */
  r0 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E420 */
  r0 = r0 + r9;                  /* 0810E422 */
  r0 = r0 - 0x1u;                /* 0810E424 */
  r0 = r0 * r2;                  /* 0810E426 */
  r2 = r1 + r0;                  /* 0810E428 */
  r0 = r5 - 0x1u;                /* 0810E42A */
  r0 = r0 << 0x10u;              /* 0810E42C */
  r5 = r0 >> 0x10u;              /* 0810E42E */
  r3 = r8;                       /* 0810E430 */
  __asm__ volatile("" : : "r"(r3));
  r3 = r3 << 0x10u; /* 0810E432 */
  r10 = r3;         /* 0810E434 */
  r7 = 0xffffu;     /* 0810E436 */
  if (r5 != r7)
    goto L_0810E43E; /* 0810E43A */
  goto L_0810E58A;   /* 0810E43C */
L_0810E43E:
  r1 = stack[0];  /* 0810E43E */
  r3 = stack[2];  /* 0810E440 */
  r0 = r1 + 0x0u; /* 0810E442 */
  r0 = r0 * r3;   /* 0810E444 */
  r8 = r0;        /* 0810E446 */
  __asm__ volatile("" : : "r"(r0));
  r12 = r7; /* 0810E448 */
L_0810E44A:
  r3 = 0x0u;                     /* 0810E44A */
  r7 = r5 - 0x1u;                /* 0810E44C */
  r0 = stack[3];                 /* 0810E44E */
  r5 = r4 + r0;                  /* 0810E450 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E452 */
  if (r3 >= r1)
    goto L_0810E47C; /* 0810E456 */
  r0 = 0x80u;        /* 0810E458 */
  r0 = r0 << 0x3u;   /* 0810E45A */
  r9 = r0;           /* 0810E45C */
L_0810E45E:
  r0 = r3 << 0x1u;                /* 0810E45E */
  r1 = r0 + r4;                   /* 0810E460 */
  stack[15] = r1;                 /* 0810E462 */
  r0 = r2 - r0;                   /* 0810E464 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E466 */
  r1 = r9;                        /* 0810E468 */
  r0 = r0 ^ r1;                   /* 0810E46A */
  r1 = stack[15];                 /* 0810E46C */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E46E */
  r0 = r3 + 0x1u;                 /* 0810E470 */
  r0 = r0 << 0x10u;               /* 0810E472 */
  r3 = r0 >> 0x10u;               /* 0810E474 */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810E476 */
  if (r3 < r0)
    goto L_0810E45E; /* 0810E47A */
L_0810E47C:
  r4 = r5 + 0x0u;   /* 0810E47C */
  r2 = r2 + r8;     /* 0810E47E */
  r0 = r7 << 0x10u; /* 0810E480 */
  r5 = r0 >> 0x10u; /* 0810E482 */
  if (r5 != r12)
    goto L_0810E44A; /* 0810E486 */
  goto L_0810E58A;   /* 0810E488 */
L_0810E490:
  r0 = 0x80u;   /* 0810E490 */
  r0 = r0 & r3; /* 0810E492 */
  if (r0 == 0x0u)
    goto L_0810E518; /* 0810E496 */
  r1 = stack[5];     /* 0810E498 */
  r0 = r1 + r5;      /* 0810E49A */
  r0 = r0 - 0x1u;    /* 0810E49C */
  r0 = r0 * r7;      /* 0810E49E */
  r2 = stack[2];     /* 0810E4A0 */
  r1 = r0 + 0x0u;    /* 0810E4A2 */
  __asm__ volatile("" : : "r"(r0));
  r1 = r1 * r2;                  /* 0810E4A4 */
  r0 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E4A6 */
  r0 = r0 + r1;                  /* 0810E4A8 */
  r3 = stack[4];                 /* 0810E4AA */
  r1 = r3 + 0x0u;                /* 0810E4AC */
  r1 = r1 * r2;                  /* 0810E4AE */
  r2 = r0 + r1;                  /* 0810E4B0 */
  r0 = r5 - 0x1u;                /* 0810E4B2 */
  r0 = r0 << 0x10u;              /* 0810E4B4 */
  r5 = r0 >> 0x10u;              /* 0810E4B6 */
  r7 = r8;                       /* 0810E4B8 */
  __asm__ volatile("" : : "r"(r8));
  r7 = r7 << 0x10u; /* 0810E4BA */
  r10 = r7;         /* 0810E4BC */
  r0 = 0xffffu;     /* 0810E4BE */
  if (r5 == r0)
    goto L_0810E58A; /* 0810E4C2 */
  r3 = stack[0];     /* 0810E4C4 */
  r7 = stack[2];     /* 0810E4C6 */
  r1 = r3 + 0x0u;    /* 0810E4C8 */
  r1 = r1 * r7;      /* 0810E4CA */
  r8 = r1;           /* 0810E4CC */
  r12 = r0;          /* 0810E4CE */
L_0810E4D0:
  r3 = 0x0u;                     /* 0810E4D0 */
  r7 = r5 - 0x1u;                /* 0810E4D2 */
  r0 = stack[3];                 /* 0810E4D4 */
  r5 = r4 + r0;                  /* 0810E4D6 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E4D8 */
  if (r3 >= r1)
    goto L_0810E502; /* 0810E4DC */
  r0 = 0x80u;        /* 0810E4DE */
  r0 = r0 << 0x4u;   /* 0810E4E0 */
  r9 = r0;           /* 0810E4E2 */
L_0810E4E4:
  r0 = r3 << 0x1u;                /* 0810E4E4 */
  r1 = r0 + r4;                   /* 0810E4E6 */
  stack[15] = r1;                 /* 0810E4E8 */
  r0 = r0 + r2;                   /* 0810E4EA */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E4EC */
  r1 = r9;                        /* 0810E4EE */
  r0 = r0 ^ r1;                   /* 0810E4F0 */
  r1 = stack[15];                 /* 0810E4F2 */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E4F4 */
  r0 = r3 + 0x1u;                 /* 0810E4F6 */
  r0 = r0 << 0x10u;               /* 0810E4F8 */
  r3 = r0 >> 0x10u;               /* 0810E4FA */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810E4FC */
  if (r3 < r0)
    goto L_0810E4E4; /* 0810E500 */
L_0810E502:
  r4 = r5 + 0x0u; /* 0810E502 */
  r1 = r8;        /* 0810E504 */
  r2 = r2 - r1;   /* 0810E506 */
  __asm__ volatile("" : : "r"(r1));
  r0 = r7 << 0x10u; /* 0810E508 */
  r5 = r0 >> 0x10u; /* 0810E50A */
  if (r5 != r12)
    goto L_0810E4D0; /* 0810E50E */
  goto L_0810E58A;   /* 0810E510 */
L_0810E518:
  r2 = stack[5];  /* 0810E518 */
  r0 = r2 + 0x0u; /* 0810E51A */
  r0 = r0 * r7;   /* 0810E51C */
  r3 = stack[2];  /* 0810E51E */
  r1 = r0 + 0x0u; /* 0810E520 */
  __asm__ volatile("" : : "r"(r0));
  r1 = r1 * r3;                  /* 0810E522 */
  r0 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E524 */
  r0 = r0 + r1;                  /* 0810E526 */
  r7 = stack[4];                 /* 0810E528 */
  r1 = r7 + 0x0u;                /* 0810E52A */
  r1 = r1 * r3;                  /* 0810E52C */
  r2 = r0 + r1;                  /* 0810E52E */
  r0 = r5 - 0x1u;                /* 0810E530 */
  r0 = r0 << 0x10u;              /* 0810E532 */
  r5 = r0 >> 0x10u;              /* 0810E534 */
  r0 = r8;                       /* 0810E536 */
  __asm__ volatile("" : : "r"(r8));
  r0 = r0 << 0x10u; /* 0810E538 */
  r10 = r0;         /* 0810E53A */
  r1 = 0xffffu;     /* 0810E53C */
  if (r5 == r1)
    goto L_0810E58A;     /* 0810E540 */
  r3 = 0x40000d4u;       /* 0810E542 */
  r0 = (int)r0 >> 0x10u; /* 0810E544 */
  r0 = r0 - 0x1u;        /* 0810E546 */
  r8 = r0;               /* 0810E548 */
  r12 = r1;              /* 0810E54A */
  r7 = 0x80u;            /* 0810E54C */
  r7 = r7 << 0x18u;      /* 0810E54E */
  r9 = r7;               /* 0810E550 */
  r1 = stack[0];         /* 0810E552 */
  r7 = stack[2];         /* 0810E554 */
  r0 = r1 + 0x0u;        /* 0810E556 */
  r0 = r0 * r7;          /* 0810E558 */
  stack[16] = r0;        /* 0810E55A */
L_0810E55C:
  *(volatile DbaaU32 *)(r3) = r2;        /* 0810E55C */
  *(volatile DbaaU32 *)(r3 + 0x4u) = r4; /* 0810E55E */
  r0 = *(DbaaU16 *)(r6 + 0x26u);         /* 0810E560 */
  r1 = r8;                               /* 0810E562 */
  r0 = r0 - r1;                          /* 0810E564 */
  __asm__ volatile("" : : "r"(r1));
  r7 = stack[2];                         /* 0810E566 */
  r0 = r0 * r7;                          /* 0810E568 */
  r1 = r0 >> 0x1fu;                      /* 0810E56A */
  r0 = r0 + r1;                          /* 0810E56C */
  r0 = (int)r0 >> 0x1u;                  /* 0810E56E */
  r1 = r9;                               /* 0810E570 */
  r0 = r0 | r1;                          /* 0810E572 */
  *(volatile DbaaU32 *)(r3 + 0x8u) = r0; /* 0810E574 */
  r0 = *(volatile DbaaU32 *)(r3 + 0x8u); /* 0810E576 */
  r7 = stack[3];                         /* 0810E578 */
  r4 = r4 + r7;                          /* 0810E57A */
  r0 = stack[16];                        /* 0810E57C */
  r2 = r2 + r0;                          /* 0810E57E */
  r0 = r5 - 0x1u;                        /* 0810E580 */
  r0 = r0 << 0x10u;                      /* 0810E582 */
  r5 = r0 >> 0x10u;                      /* 0810E584 */
  if (r5 != r12)
    goto L_0810E55C; /* 0810E588 */
L_0810E58A:
  r1 = r10;              /* 0810E58A */
  r7 = (int)r1 >> 0x10u; /* 0810E58C */
  if (r7 != 0x0u)
    goto L_0810E594; /* 0810E590 */
  goto L_0810E8C2;   /* 0810E592 */
L_0810E594:
  r0 = *(DbaaU16 *)(r6 + 0x24u); /* 0810E594 */
  r2 = stack[3];                 /* 0810E596 */
  r0 = r0 * r2;                  /* 0810E598 */
  r1 = *(DbaaU32 *)(r6 + 0xcu);  /* 0810E59A */
  r1 = r1 + r0;                  /* 0810E59C */
  r0 = *(DbaaU16 *)(r6 + 0x22u); /* 0810E59E */
  r2 = *(DbaaU16 *)(r6 + 0x14u); /* 0810E5A0 */
  r0 = r0 + r2;                  /* 0810E5A2 */
  r3 = stack[4];                 /* 0810E5A4 */
  r0 = r0 - r3;                  /* 0810E5A6 */
  r4 = stack[2];                 /* 0810E5A8 */
  r0 = r0 * r4;                  /* 0810E5AA */
  r4 = r1 + r0;                  /* 0810E5AC */
  r0 = *(DbaaU16 *)(r6 + 0x28u); /* 0810E5AE */
  r0 = r0 + 0x1u;                /* 0810E5B0 */
  r0 = r0 << 0x10u;              /* 0810E5B2 */
  r5 = r0 >> 0x10u;              /* 0810E5B4 */
  r1 = *(DbaaU16 *)(r6 + 0x2eu); /* 0810E5B6 */
  r3 = 0x80u;                    /* 0810E5B8 */
  r3 = r3 << 0x1u;               /* 0810E5BA */
  r0 = r3 + 0x0u;                /* 0810E5BC */
  __asm__ volatile("" : : "r"(r3));
  r0 = r0 & r1; /* 0810E5BE */
  if (r0 == 0x0u)
    goto L_0810E6BC; /* 0810E5C2 */
  r0 = 0x80u;        /* 0810E5C4 */
  r0 = r0 & r1;      /* 0810E5C6 */
  if (r0 == 0x0u)
    goto L_0810E648;             /* 0810E5CA */
  r1 = stack[5];                 /* 0810E5CC */
  r0 = r1 + r5;                  /* 0810E5CE */
  r0 = r0 - 0x1u;                /* 0810E5D0 */
  r0 = r0 * r2;                  /* 0810E5D2 */
  r2 = stack[2];                 /* 0810E5D4 */
  r0 = r0 * r2;                  /* 0810E5D6 */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E5D8 */
  r1 = r1 + r0;                  /* 0810E5DA */
  r0 = r7 - 0x1u;                /* 0810E5DC */
  r0 = r0 * r2;                  /* 0810E5DE */
  r2 = r1 + r0;                  /* 0810E5E0 */
  r0 = r5 - 0x1u;                /* 0810E5E2 */
  r0 = r0 << 0x10u;              /* 0810E5E4 */
  r5 = r0 >> 0x10u;              /* 0810E5E6 */
  r3 = 0xffffu;                  /* 0810E5E8 */
  if (r5 != r3)
    goto L_0810E5F0; /* 0810E5EC */
  goto L_0810E8C2;   /* 0810E5EE */
L_0810E5F0:
  r0 = stack[0];  /* 0810E5F0 */
  r1 = stack[2];  /* 0810E5F2 */
  r7 = r0 + 0x0u; /* 0810E5F4 */
  r7 = r7 * r1;   /* 0810E5F6 */
  r8 = r7;        /* 0810E5F8 */
  r10 = r3;       /* 0810E5FA */
L_0810E5FC:
  r3 = 0x0u;                     /* 0810E5FC */
  r7 = r5 - 0x1u;                /* 0810E5FE */
  r0 = stack[3];                 /* 0810E600 */
  r5 = r4 + r0;                  /* 0810E602 */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E604 */
  if (r3 >= r1)
    goto L_0810E62E; /* 0810E608 */
  r0 = 0xc0u;        /* 0810E60A */
  r0 = r0 << 0x4u;   /* 0810E60C */
  r9 = r0;           /* 0810E60E */
L_0810E610:
  r0 = r3 << 0x1u;                /* 0810E610 */
  r1 = r0 + r4;                   /* 0810E612 */
  r12 = r1;                       /* 0810E614 */
  r0 = r2 - r0;                   /* 0810E616 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E618 */
  r1 = r9;                        /* 0810E61A */
  r0 = r0 ^ r1;                   /* 0810E61C */
  r1 = r12;                       /* 0810E61E */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E620 */
  r0 = r3 + 0x1u;                 /* 0810E622 */
  r0 = r0 << 0x10u;               /* 0810E624 */
  r3 = r0 >> 0x10u;               /* 0810E626 */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810E628 */
  if (r3 < r0)
    goto L_0810E610; /* 0810E62C */
L_0810E62E:
  r4 = r5 + 0x0u;   /* 0810E62E */
  r1 = r8;          /* 0810E630 */
  r2 = r2 - r1;     /* 0810E632 */
  r0 = r7 << 0x10u; /* 0810E634 */
  r5 = r0 >> 0x10u; /* 0810E636 */
  if (r5 != r10)
    goto L_0810E5FC; /* 0810E63A */
  goto L_0810E8C2;   /* 0810E63C */
L_0810E648:
  r3 = stack[5];                 /* 0810E648 */
  r0 = r3 + 0x0u;                /* 0810E64A */
  r0 = r0 * r2;                  /* 0810E64C */
  r1 = stack[2];                 /* 0810E64E */
  r0 = r0 * r1;                  /* 0810E650 */
  r1 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E652 */
  r1 = r1 + r0;                  /* 0810E654 */
  r0 = r7 - 0x1u;                /* 0810E656 */
  r2 = stack[2];                 /* 0810E658 */
  r0 = r0 * r2;                  /* 0810E65A */
  r2 = r1 + r0;                  /* 0810E65C */
  r0 = r5 - 0x1u;                /* 0810E65E */
  r0 = r0 << 0x10u;              /* 0810E660 */
  r5 = r0 >> 0x10u;              /* 0810E662 */
  r3 = 0xffffu;                  /* 0810E664 */
  if (r5 != r3)
    goto L_0810E66C; /* 0810E668 */
  goto L_0810E8C2;   /* 0810E66A */
L_0810E66C:
  r0 = stack[0];  /* 0810E66C */
  r1 = stack[2];  /* 0810E66E */
  r7 = r0 + 0x0u; /* 0810E670 */
  r7 = r7 * r1;   /* 0810E672 */
  r8 = r7;        /* 0810E674 */
  r10 = r3;       /* 0810E676 */
L_0810E678:
  r3 = 0x0u;                     /* 0810E678 */
  r7 = r5 - 0x1u;                /* 0810E67A */
  r0 = stack[3];                 /* 0810E67C */
  r5 = r4 + r0;                  /* 0810E67E */
  r1 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E680 */
  if (r3 >= r1)
    goto L_0810E6AA; /* 0810E684 */
  r0 = 0x80u;        /* 0810E686 */
  r0 = r0 << 0x3u;   /* 0810E688 */
  r9 = r0;           /* 0810E68A */
L_0810E68C:
  r0 = r3 << 0x1u;                /* 0810E68C */
  r1 = r0 + r4;                   /* 0810E68E */
  r12 = r1;                       /* 0810E690 */
  r0 = r2 - r0;                   /* 0810E692 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E694 */
  r1 = r9;                        /* 0810E696 */
  r0 = r0 ^ r1;                   /* 0810E698 */
  r1 = r12;                       /* 0810E69A */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E69C */
  r0 = r3 + 0x1u;                 /* 0810E69E */
  r0 = r0 << 0x10u;               /* 0810E6A0 */
  r3 = r0 >> 0x10u;               /* 0810E6A2 */
  r0 = *(DbaaU16 *)(r6 + 0x26u);  /* 0810E6A4 */
  if (r3 < r0)
    goto L_0810E68C; /* 0810E6A8 */
L_0810E6AA:
  r4 = r5 + 0x0u;   /* 0810E6AA */
  r2 = r2 + r8;     /* 0810E6AC */
  r0 = r7 << 0x10u; /* 0810E6AE */
  r5 = r0 >> 0x10u; /* 0810E6B0 */
  if (r5 != r10)
    goto L_0810E678; /* 0810E6B4 */
  goto L_0810E8C2;   /* 0810E6B6 */
L_0810E6BC:
  r0 = 0x80u;   /* 0810E6BC */
  r0 = r0 & r1; /* 0810E6BE */
  if (r0 == 0x0u)
    goto L_0810E740;             /* 0810E6C2 */
  r1 = stack[5];                 /* 0810E6C4 */
  r0 = r1 + r5;                  /* 0810E6C6 */
  r0 = r0 - 0x1u;                /* 0810E6C8 */
  r0 = r0 * r2;                  /* 0810E6CA */
  r2 = stack[2];                 /* 0810E6CC */
  r1 = r0 + 0x0u;                /* 0810E6CE */
  r1 = r1 * r2;                  /* 0810E6D0 */
  r0 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E6D2 */
  r2 = r0 + r1;                  /* 0810E6D4 */
  r0 = r5 - 0x1u;                /* 0810E6D6 */
  r0 = r0 << 0x10u;              /* 0810E6D8 */
  r5 = r0 >> 0x10u;              /* 0810E6DA */
  r3 = 0xffffu;                  /* 0810E6DC */
  if (r5 != r3)
    goto L_0810E6E4; /* 0810E6E0 */
  goto L_0810E8C2;   /* 0810E6E2 */
L_0810E6E4:
  r0 = r10;       /* 0810E6E4 */
  stack[12] = r0; /* 0810E6E6 */
  r10 = r7;       /* 0810E6E8 */
  r3 = stack[0];  /* 0810E6EA */
  r7 = stack[2];  /* 0810E6EC */
  r1 = r3 + 0x0u; /* 0810E6EE */
  r1 = r1 * r7;   /* 0810E6F0 */
  r8 = r1;        /* 0810E6F2 */
L_0810E6F4:
  r3 = 0x0u;      /* 0810E6F4 */
  r7 = r5 - 0x1u; /* 0810E6F6 */
  r0 = stack[3];  /* 0810E6F8 */
  r5 = r4 + r0;   /* 0810E6FA */
  if ((int)r3 >= (int)r10)
    goto L_0810E728; /* 0810E6FE */
  r1 = 0x80u;        /* 0810E700 */
  r1 = r1 << 0x4u;   /* 0810E702 */
  r9 = r1;           /* 0810E704 */
  __asm__ volatile("" : : "r"(r1));
  r0 = stack[12];        /* 0810E706 */
  r0 = (int)r0 >> 0x10u; /* 0810E708 */
  r12 = r0;              /* 0810E70A */
L_0810E70C:
  r0 = r3 << 0x1u;                /* 0810E70C */
  r1 = r0 + r4;                   /* 0810E70E */
  stack[15] = r1;                 /* 0810E710 */
  r0 = r0 + r2;                   /* 0810E712 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E714 */
  r1 = r9;                        /* 0810E716 */
  r0 = r0 ^ r1;                   /* 0810E718 */
  r1 = stack[15];                 /* 0810E71A */
  *(volatile DbaaU16 *)(r1) = r0; /* 0810E71C */
  r0 = r3 + 0x1u;                 /* 0810E71E */
  r0 = r0 << 0x10u;               /* 0810E720 */
  r3 = r0 >> 0x10u;               /* 0810E722 */
  if ((int)r3 < (int)r12)
    goto L_0810E70C; /* 0810E726 */
L_0810E728:
  r4 = r5 + 0x0u;   /* 0810E728 */
  r3 = r8;          /* 0810E72A */
  r2 = r2 - r3;     /* 0810E72C */
  r0 = r7 << 0x10u; /* 0810E72E */
  r5 = r0 >> 0x10u; /* 0810E730 */
  r7 = 0xffffu;     /* 0810E732 */
  if (r5 != r7)
    goto L_0810E6F4; /* 0810E736 */
  goto L_0810E8C2;   /* 0810E738 */
L_0810E740:
  r1 = stack[5];                 /* 0810E740 */
  r0 = r1 + 0x0u;                /* 0810E742 */
  r0 = r0 * r2;                  /* 0810E744 */
  r2 = stack[2];                 /* 0810E746 */
  r1 = r0 + 0x0u;                /* 0810E748 */
  r1 = r1 * r2;                  /* 0810E74A */
  r0 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E74C */
  r2 = r0 + r1;                  /* 0810E74E */
  r0 = r5 - 0x1u;                /* 0810E750 */
  r0 = r0 << 0x10u;              /* 0810E752 */
  r5 = r0 >> 0x10u;              /* 0810E754 */
  r3 = 0xffffu;                  /* 0810E756 */
  if (r5 != r3)
    goto L_0810E75E; /* 0810E75A */
  goto L_0810E8C2;   /* 0810E75C */
L_0810E75E:
  r3 = 0x40000d4u;      /* 0810E75E */
  r1 = stack[2];        /* 0810E760 */
  r0 = r7 + 0x0u;       /* 0810E762 */
  r0 = r0 * r1;         /* 0810E764 */
  r1 = r0 >> 0x1fu;     /* 0810E766 */
  r0 = r0 + r1;         /* 0810E768 */
  r0 = (int)r0 >> 0x1u; /* 0810E76A */
  r8 = r0;              /* 0810E76C */
  r0 = 0x80u;           /* 0810E76E */
  r0 = r0 << 0x18u;     /* 0810E770 */
  r7 = r8;              /* 0810E772 */
  r7 = r7 | r0;         /* 0810E774 */
  r8 = r7;              /* 0810E776 */
  r1 = stack[0];        /* 0810E778 */
  r7 = stack[2];        /* 0810E77A */
  r0 = r1 + 0x0u;       /* 0810E77C */
  r0 = r0 * r7;         /* 0810E77E */
  r9 = r0;              /* 0810E780 */
L_0810E782:
  *(volatile DbaaU32 *)(r3) = r2;        /* 0810E782 */
  *(volatile DbaaU32 *)(r3 + 0x4u) = r4; /* 0810E784 */
  r0 = r8;                               /* 0810E786 */
  *(volatile DbaaU32 *)(r3 + 0x8u) = r0; /* 0810E788 */
  r0 = *(volatile DbaaU32 *)(r3 + 0x8u); /* 0810E78A */
  r1 = stack[3];                         /* 0810E78C */
  r4 = r4 + r1;                          /* 0810E78E */
  r2 = r2 + r9;                          /* 0810E790 */
  r0 = r5 - 0x1u;                        /* 0810E792 */
  r0 = r0 << 0x10u;                      /* 0810E794 */
  r5 = r0 >> 0x10u;                      /* 0810E796 */
  r7 = 0xffffu;                          /* 0810E798 */
  if (r5 != r7)
    goto L_0810E782; /* 0810E79C */
  goto L_0810E8C2;   /* 0810E79E */
/* Scrolling metatiles: compute wrapped coordinates and clipped DMA chunks. */
L_0810E7A8:
  r0 = r4 >> 0x3u;               /* 0810E7A8 */
  r1 = *(DbaaU16 *)(r6 + 0x1eu); /* 0810E7AA */
  r0 = r0 + r1;                  /* 0810E7AC */
  r0 = r0 << 0x10u;              /* 0810E7AE */
  r0 = r0 >> 0x10u;              /* 0810E7B0 */
  stack[4] = r0;                 /* 0810E7B2 */
  r0 = *(DbaaU16 *)(r6 + 0x32u); /* 0810E7B4 */
  r0 = r0 >> 0x3u;               /* 0810E7B6 */
  r2 = *(DbaaU16 *)(r6 + 0x20u); /* 0810E7B8 */
  r0 = r0 + r2;                  /* 0810E7BA */
  r0 = r0 << 0x10u;              /* 0810E7BC */
  r0 = r0 >> 0x10u;              /* 0810E7BE */
  stack[5] = r0;                 /* 0810E7C0 */
  r3 = 0x0u;                     /* 0810E7C2 */
  r10 = r3;                      /* 0810E7C4 */
  __asm__ volatile("" : : "r"(r3));
  r4 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E7C6 */
  if ((int)r10 >= (int)r4)
    goto L_0810E8C2; /* 0810E7CA */
L_0810E7CC:
  r4 = stack[4];                            /* 0810E7CC */
  r4 = r4 + r10;                            /* 0810E7CE */
  r1 = *(DbaaU16 *)(r6 + 0x14u);            /* 0810E7D0 */
  r0 = r4 + 0x0u;                           /* 0810E7D2 */
  r0 = (DbaaU32)Bios_Div((int)r0, (int)r1); /* 0810E7D4 */
  stack[9] = r0;                            /* 0810E7D8 */
  r1 = *(DbaaU16 *)(r6 + 0x14u);            /* 0810E7DA */
  r7 = r0 + 0x0u;                           /* 0810E7DC */
anchor_4:;
  r0 = r7 + 0x0u;                         /* 0810E7DE */
  r0 = r0 * r1;                           /* 0810E7E0 */
  r4 = r4 - r0;                           /* 0810E7E2 */
  stack[10] = r4;                         /* 0810E7E4 */
  r0 = *(volatile DbaaU16 *)(r6 + 0x28u); /* 0810E7E6 */
  r8 = r0;                                /* 0810E7E8 */
  r0 = *(DbaaU16 *)(r6 + 0x26u);          /* 0810E7EA */
  r2 = r10;                               /* 0810E7EC */
  r0 = r0 - r2;                           /* 0810E7EE */
  r1 = r1 - r4;                           /* 0810E7F0 */
  if ((int)r1 <= (int)r0)
    goto L_0810E7F8; /* 0810E7F4 */
  r1 = r0 + 0x0u;    /* 0810E7F6 */
L_0810E7F8:
  r4 = stack[2];  /* 0810E7F8 */
  r3 = r1 + 0x0u; /* 0810E7FA */
  r3 = r3 * r4;   /* 0810E7FC */
  stack[11] = r3; /* 0810E7FE */
  r7 = 0x0u;      /* 0810E800 */
  __asm__ volatile("" : "+r"(r7));
  r9 = r7;        /* 0810E802 */
  r1 = r1 + r10;  /* 0810E804 */
  stack[13] = r1; /* 0810E806 */
  if ((int)r9 >= (int)r8)
    goto L_0810E8B8; /* 0810E80A */
L_0810E80C:
  r4 = stack[5];                            /* 0810E80C */
  r4 = r4 + r9;                             /* 0810E80E */
  r1 = *(DbaaU16 *)(r6 + 0x16u);            /* 0810E810 */
  r0 = r4 + 0x0u;                           /* 0810E812 */
  r0 = (DbaaU32)Bios_Div((int)r0, (int)r1); /* 0810E814 */
  r3 = *(DbaaU16 *)(r6 + 0x16u);            /* 0810E818 */
  r1 = r0 + 0x0u;                           /* 0810E81A */
  r1 = r1 * r3;                             /* 0810E81C */
  r4 = r4 - r1;                             /* 0810E81E */
  r5 = r3 - r4;                             /* 0810E820 */
  r1 = *(DbaaU16 *)(r6 + 0x3cu);            /* 0810E822 */
  r1 = r1 << 0x1u;                          /* 0810E824 */
  r1 = r1 * r0;                             /* 0810E826 */
  r0 = stack[9];                            /* 0810E828 */
  r2 = r0 << 0x1u;                          /* 0810E82A */
  r0 = *(DbaaU32 *)(r6 + 0x38u);            /* 0810E82C */
  r0 = r0 + r1;                             /* 0810E82E */
  r0 = r0 + r2;                             /* 0810E830 */
  r0 = *(volatile DbaaU16 *)(r0);           /* 0810E832 */
  r2 = *(DbaaU16 *)(r6 + 0x14u);            /* 0810E834 */
anchor_5:;
  r0 = r0 * r2;   /* 0810E836 */
  r1 = r0 + 0x0u; /* 0810E838 */
anchor_6:;
  r1 = r1 * r3;                  /* 0810E83A */
  r0 = r4 + 0x0u;                /* 0810E83C */
  r0 = r0 * r2;                  /* 0810E83E */
  r2 = stack[10];                /* 0810E840 */
  r0 = r0 + r2;                  /* 0810E842 */
  r1 = r1 + r0;                  /* 0810E844 */
  r3 = stack[2];                 /* 0810E846 */
  r1 = r1 * r3;                  /* 0810E848 */
  r0 = *(DbaaU32 *)(r6 + 0x10u); /* 0810E84A */
  r0 = r0 + r1;                  /* 0810E84C */
  stack[16] = r0;                /* 0810E84E */
  r1 = *(DbaaU16 *)(r6 + 0x24u); /* 0810E850 */
  r0 = *(DbaaU32 *)(r6 + 0xcu);  /* 0810E852 */
  r0 = r0 + r1;                  /* 0810E854 */
  r4 = stack[3];                 /* 0810E856 */
  r1 = r9;                       /* 0810E858 */
  r1 = r1 * r4;                  /* 0810E85A */
  r0 = r0 + r1;                  /* 0810E85C */
  r7 = *(DbaaU16 *)(r6 + 0x22u); /* 0810E85E */
  r0 = r0 + r7;                  /* 0810E860 */
  r1 = r10;                      /* 0810E862 */
  r1 = r1 * r3;                  /* 0810E864 */
  r3 = r0 + r1;                  /* 0810E866 */
  r9 = r9 + r5;                  /* 0810E868 */
  if ((int)r5 <= (int)r8)
    goto L_0810E870; /* 0810E86C */
  r5 = r8;           /* 0810E86E */
L_0810E870:
  r0 = r8; /* 0810E870 */
anchor_7:;
  r0 = r0 - r5;   /* 0810E872 */
  r8 = r0;        /* 0810E874 */
  r0 = r5 + 0x0u; /* 0810E876 */
  r5 = r5 - 0x1u; /* 0810E878 */
  if (r0 == 0x0u)
    goto L_0810E8B2;    /* 0810E87C */
  r2 = 0x40000d4u;      /* 0810E87E */
  r1 = stack[11];       /* 0810E880 */
  r0 = r1 >> 0x1fu;     /* 0810E882 */
  r0 = r1 + r0;         /* 0810E884 */
  r1 = (int)r0 >> 0x1u; /* 0810E886 */
  r0 = 0x80u;           /* 0810E888 */
  r0 = r0 << 0x18u;     /* 0810E88A */
  r1 = r1 | r0;         /* 0810E88C */
  r7 = stack[0];        /* 0810E88E */
  r0 = stack[2];        /* 0810E890 */
  r4 = r7 + 0x0u;       /* 0810E892 */
  r4 = r4 * r0;         /* 0810E894 */
  r12 = r4;             /* 0810E896 */
L_0810E898:
  r4 = stack[16];                        /* 0810E898 */
  *(volatile DbaaU32 *)(r2) = r4;        /* 0810E89A */
  *(volatile DbaaU32 *)(r2 + 0x4u) = r3; /* 0810E89C */
  *(volatile DbaaU32 *)(r2 + 0x8u) = r1; /* 0810E89E */
  r0 = *(volatile DbaaU32 *)(r2 + 0x8u); /* 0810E8A0 */
  r7 = stack[3];                         /* 0810E8A2 */
  r3 = r3 + r7;                          /* 0810E8A4 */
  r4 = r4 + r12;                         /* 0810E8A6 */
  stack[16] = r4;                        /* 0810E8A8 */
  r0 = r5 + 0x0u;                        /* 0810E8AA */
  r5 = r5 - 0x1u;                        /* 0810E8AC */
  if (r0 != 0x0u)
    goto L_0810E898; /* 0810E8B0 */
L_0810E8B2:
  r0 = *(DbaaU16 *)(r6 + 0x28u); /* 0810E8B2 */
  if ((int)r9 < (int)r0)
    goto L_0810E80C; /* 0810E8B6 */
L_0810E8B8:
  r1 = stack[13];                /* 0810E8B8 */
  r10 = r1;                      /* 0810E8BA */
  r2 = *(DbaaU16 *)(r6 + 0x26u); /* 0810E8BC */
  if ((int)r10 < (int)r2)
    goto L_0810E7CC; /* 0810E8C0 */
/* Poll VCOUNT, then continue while queue read/write indices differ. */
L_0810E8C2:
anchor_8:;
  r0 = 0x4000006u;                /* 0810E8C2 */
  r0 = *(volatile DbaaU16 *)(r0); /* 0810E8C4 */
  r0 = *(DbaaU16 *)(r6 + 0x30u);  /* 0810E8C6 */
  *(DbaaU16 *)(r6 + 0x34u) = r0;  /* 0810E8C8 */
  r0 = *(DbaaU16 *)(r6 + 0x32u);  /* 0810E8CA */
  *(DbaaU16 *)(r6 + 0x36u) = r0;  /* 0810E8CC */
  r3 = 0x3003f74u;                /* 0810E8CE */
  r4 = 0x3003d00u;                /* 0810E8D0 */
L_0810E8D2:
  r0 = *(volatile DbaaU8 *)(r3); /* 0810E8D2 */
  r7 = *(DbaaU8 *)(r4);          /* 0810E8D4 */
  if (r0 == r7)
    goto L_0810E8DE; /* 0810E8D8 */
  goto L_0810DDF0;   /* 0810E8DA */
L_0810E8DE:
  r0 = 0x1u; /* 0810E8DE */
L_0810E8E0:
  return r0;
}
