/*
 * USA 080EEDB4..080EEFE8: 564 complete bytes match the ROM.
 * C register/data-flow reconstruction for agbcc -O1 -mthumb-interwork.
 * All instructions are emitted from C; every asm template is empty.
 * No opcode arrays, instruction templates or compiler-output editing.
 *
 * Readable algorithm: reference/post_boot_load_background.c (not a match
 * target). The three volatile stack words retain bg, resource id and bg*4. r4
 * is the row; r5 is the width; r6 changes from height to count/flip mask; r7 is
 * the entry; r8 holds height; r9 changes from map to height; r10 is the map
 * destination; r12 holds the palette bits. Raw addresses are fixed to the USA
 * ROM and its existing symbol map. See docs/post_boot_loader_matching.md for
 * limits and reproduction.
 */
#include "backgrounds.h"
#include "post_boot.h"
void PostBoot_LoadBackground(DbaaU8 index) {
  volatile DbaaU32 stack[3];
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
  /* Resolve the signed resource id before the special-index dispatch. */
  r2 = index;
  r0 = r2 << 0x1u;                                                /* 080EEDC4 */
  r0 = r0 + r2;                                                   /* 080EEDC6 */
  r0 = r0 << 0x2u;                                                /* 080EEDC8 */
  r1 = 0x08A4E33Cu;                                               /* 080EEDCA */
  r7 = r0 + r1;                                                   /* 080EEDCC */
  r0 = *(volatile DbaaU8 *)(r7);                                  /* 080EEDCE */
  stack[0] = r0;                                                  /* 080EEDD0 */
  r0 = ((const struct DbaaPostBootBackground *)r7)->backgroundId; /* 080EEDD4 */
  __asm__("" : : "r"(r0));
  if ((int)r0 < (int)0x0u)
    goto L_080EEDE4;                     /* 080EEDD8 */
  r0 = *(volatile DbaaU16 *)(r7 + 0x2u); /* 080EEDDA */
  goto L_080EEDE8;                       /* 080EEDDC */
L_080EEDE4:
  r0 = 0x08A4E338u;               /* 080EEDE4 */
  r0 = *(volatile DbaaU16 *)(r0); /* 080EEDE6 */
L_080EEDE8:
  stack[1] = r0; /* 080EEDE8 */
  if (r2 != 0xAu)
    goto L_080EEDFC;                          /* 080EEDEC */
  r0 = 0xAu;                                  /* 080EEDEE */
  PostBoot_LoadSpecialBackground((DbaaU8)r0); /* 080EEDF0 */
  goto L_080EEFC4;                            /* 080EEDF4 */
/* Select BG priority, character memory and map screenblock. */
L_080EEDFC:
  r0 = 0x03003120u; /* 080EEDFC */
  __asm__("" : : "r"(r0));
  r2 = stack[0];                        /* 080EEDFE */
  r1 = r2 << 0x1u;                      /* 080EEE00 */
  r1 = r1 + r0;                         /* 080EEE02 */
  r2 = *(volatile DbaaU16 *)(r1);       /* 080EEE04 */
  r0 = 0xFFFCu;                         /* 080EEE06 */
  r0 = r0 & r2;                         /* 080EEE08 */
  *(volatile DbaaU16 *)(r1) = r0;       /* 080EEE0A */
  r2 = *(volatile DbaaU8 *)(r7 + 0x1u); /* 080EEE0C */
  r2 = r2 | r0;                         /* 080EEE0E */
  *(volatile DbaaU16 *)(r1) = r2;       /* 080EEE10 */
  r1 = 0x0882323Cu;                     /* 080EEE12 */
  __asm__("" : : "r"(r1));
  r3 = stack[1];                                     /* 080EEE14 */
  r0 = r3 << 0x2u;                                   /* 080EEE16 */
  r0 = r0 + r1;                                      /* 080EEE18 */
  r4 = *(volatile DbaaU32 *)(r0);                    /* 080EEE1A */
  r0 = *(volatile DbaaU32 *)(r4 + 0x8u);             /* 080EEE1C */
  r5 = *(volatile DbaaU32 *)(r4 + 0x18u);            /* 080EEE1E */
  r9 = r5;                                           /* 080EEE20 */
  r2 = r2 << 0x10u;                                  /* 080EEE22 */
  r1 = r2 >> 0x12u;                                  /* 080EEE24 */
  r3 = 0x3u;                                         /* 080EEE26 */
  r1 = r1 & r3;                                      /* 080EEE28 */
  r2 = r2 >> 0x18u;                                  /* 080EEE2A */
  r3 = 0x1Fu;                                        /* 080EEE2C */
  r2 = r2 & r3;                                      /* 080EEE2E */
  r2 = r2 << 0xBu;                                   /* 080EEE30 */
  r3 = 0xC0u;                                        /* 080EEE32 */
  r3 = r3 << 0x13u;                                  /* 080EEE34 */
  r2 = r2 + r3;                                      /* 080EEE36 */
  r10 = r2;                                          /* 080EEE38 */
  r5 = *(volatile DbaaU8 *)(r4);                     /* 080EEE3A */
  r6 = *(volatile DbaaU8 *)(r4 + 0x2u);              /* 080EEE3C */
  r1 = r1 << 0xEu;                                   /* 080EEE3E */
  r1 = r1 + r3;                                      /* 080EEE40 */
  Bios_LZ77UnCompVram((const void *)r0, (void *)r1); /* 080EEE42 */
  /* Normal row copies and mirrored copies have distinct loop counters. */
  r0 = *(volatile DbaaU8 *)(r7 + 0x7u); /* 080EEE46 */
  if (r0 != 0x0u)
    goto L_080EEE90; /* 080EEE4A */
  r0 = r6 << 0x10u;  /* 080EEE4C */
  __asm__("" : : "r"(r0));
  r4 = 0x0u;       /* 080EEE4E */
  r8 = r0;         /* 080EEE50 */
  r0 = stack[0];   /* 080EEE52 */
  r0 = r0 << 0x2u; /* 080EEE54 */
  stack[2] = r0;   /* 080EEE56 */
  r1 = r8;         /* 080EEE58 */
  __asm__("" : : "r"(r1));
  if (r1 == 0x0u)
    goto L_080EEEDC; /* 080EEE5C */
  r6 = r5 + 0x0u;    /* 080EEE5E */
L_080EEE60:
  r0 = r5 + 0x0u;                                /* 080EEE60 */
  r0 = r0 * r4;                                  /* 080EEE62 */
  r0 = r0 << 0x1u;                               /* 080EEE64 */
  r0 = r0 + r9;                                  /* 080EEE66 */
  r1 = r4 << 0x6u;                               /* 080EEE68 */
  r1 = r1 + r10;                                 /* 080EEE6A */
  r2 = 0x1FFFFFu;                                /* 080EEE6C */
  r2 = r2 & r6;                                  /* 080EEE6E */
  Bios_CpuSet((const void *)r0, (void *)r1, r2); /* 080EEE70 */
  r0 = r4 + 0x1u;                                /* 080EEE74 */
  r0 = r0 << 0x10u;                              /* 080EEE76 */
  r4 = r0 >> 0x10u;                              /* 080EEE78 */
  if (r0 < r8)
    goto L_080EEE60; /* 080EEE7C */
  goto L_080EEEDC;   /* 080EEE7E */
L_080EEE90:
  r3 = r9;          /* 080EEE90 */
  r4 = 0x0u;        /* 080EEE92 */
  r0 = r6 << 0x10u; /* 080EEE94 */
  r1 = r0 >> 0x10u; /* 080EEE96 */
  r8 = r0;          /* 080EEE98 */
  r2 = stack[0];    /* 080EEE9A */
  r2 = r2 << 0x2u;  /* 080EEE9C */
  stack[2] = r2;    /* 080EEE9E */
  if (r4 >= r1)
    goto L_080EEEDC; /* 080EEEA2 */
  r9 = r1;           /* 080EEEA4 */
L_080EEEA6:
  r0 = r4 << 0x5u; /* 080EEEA6 */
  r0 = r0 - 0x1u;  /* 080EEEA8 */
  r0 = r0 + r5;    /* 080EEEAA */
  r0 = r0 << 0x1u; /* 080EEEAC */
  r2 = r10;        /* 080EEEAE */
  r1 = r2 + r0;    /* 080EEEB0 */
  r2 = 0x0u;       /* 080EEEB2 */
  r4 = r4 + 0x1u;  /* 080EEEB4 */
  if (r2 >= r5)
    goto L_080EEED4; /* 080EEEB8 */
  r0 = 0x80u;        /* 080EEEBA */
  r0 = r0 << 0x3u;   /* 080EEEBC */
  __asm__("" : : "r"(r0));
  r6 = r0 + 0x0u; /* 080EEEBE */
L_080EEEC0:
  r0 = *(volatile DbaaU16 *)(r3); /* 080EEEC0 */
  r0 = r0 ^ r6;                   /* 080EEEC2 */
  *(volatile DbaaU16 *)(r1) = r0; /* 080EEEC4 */
  r3 = r3 + 0x2u;                 /* 080EEEC6 */
  r1 = r1 - 0x2u;                 /* 080EEEC8 */
  r0 = r2 + 0x1u;                 /* 080EEECA */
  r0 = r0 << 0x18u;               /* 080EEECC */
  r2 = r0 >> 0x18u;               /* 080EEECE */
  if (r2 < r5)
    goto L_080EEEC0; /* 080EEED2 */
L_080EEED4:
  r0 = r4 << 0x10u; /* 080EEED4 */
  r4 = r0 >> 0x10u; /* 080EEED6 */
  if (r4 < r9)
    goto L_080EEEA6; /* 080EEEDA */
/* Replace only the palette nibble, preserving tile index and flip bits. */
L_080EEEDC:
  r0 = *(volatile DbaaU8 *)(r7 + 0x4u); /* 080EEEDC */
  __asm__("" : : "r"(r0));
  r1 = *(volatile DbaaU8 *)(r7 + 0x5u); /* 080EEEDE */
  if (r0 == r1)
    goto L_080EEF28;                    /* 080EEEE2 */
  r0 = *(volatile DbaaU8 *)(r7 + 0x5u); /* 080EEEE4 */
  r0 = r0 << 0x1Cu;                     /* 080EEEE6 */
  r0 = r0 >> 0x10u;                     /* 080EEEE8 */
  r12 = r0;                             /* 080EEEEA */
  r4 = 0x0u;                            /* 080EEEEC */
  r2 = r8;                              /* 080EEEEE */
  __asm__("" : : "r"(r2));
  r0 = r2 >> 0x10u; /* 080EEEF0 */
  if (r4 >= r0)
    goto L_080EEF28; /* 080EEEF4 */
  r8 = r0;           /* 080EEEF6 */
L_080EEEF8:
  r0 = r4 << 0x6u; /* 080EEEF8 */
  r3 = r10;        /* 080EEEFA */
  __asm__("" : : "r"(r3));
  r2 = r3 + r0;   /* 080EEEFC */
  r3 = 0x0u;      /* 080EEEFE */
  r4 = r4 + 0x1u; /* 080EEF00 */
  if (r3 >= r5)
    goto L_080EEF20; /* 080EEF04 */
  r6 = 0xFFFu;       /* 080EEF06 */
L_080EEF08:
  r0 = *(volatile DbaaU16 *)(r2); /* 080EEF08 */
  r1 = r6 + 0x0u;                 /* 080EEF0A */
  __asm__("" : : "r"(r1));
  r1 = r1 & r0;                   /* 080EEF0C */
  r0 = r12;                       /* 080EEF0E */
  r1 = r1 | r0;                   /* 080EEF10 */
  *(volatile DbaaU16 *)(r2) = r1; /* 080EEF12 */
  r2 = r2 + 0x2u;                 /* 080EEF14 */
  r0 = r3 + 0x1u;                 /* 080EEF16 */
  r0 = r0 << 0x18u;               /* 080EEF18 */
  r3 = r0 >> 0x18u;               /* 080EEF1A */
  if (r3 < r5)
    goto L_080EEF08; /* 080EEF1E */
L_080EEF20:
  r0 = r4 << 0x10u; /* 080EEF20 */
  r4 = r0 >> 0x10u; /* 080EEF22 */
  if (r4 < r8)
    goto L_080EEEF8; /* 080EEF26 */
/* Palette service or DMA path; both join the color-zero/scroll commit. */
L_080EEF28:
  r0 = *(volatile DbaaU8 *)(r7 + 0x6u); /* 080EEF28 */
  if (r0 == 0x0u)
    goto L_080EEFA0;              /* 080EEF2C */
  r4 = 0x03002BA0u;               /* 080EEF2E */
  r3 = *(volatile DbaaU32 *)(r4); /* 080EEF30 */
  r0 = 0x80u;                     /* 080EEF32 */
  r0 = r0 << 0x9u;                /* 080EEF34 */
  r0 = r0 & r3;                   /* 080EEF36 */
  if (r0 == 0x0u)
    goto L_080EEF6C; /* 080EEF3A */
  r1 = 0x0882323Cu;  /* 080EEF3C */
  __asm__("" : : "r"(r1));
  r2 = stack[1];                          /* 080EEF3E */
  r0 = r2 << 0x2u;                        /* 080EEF40 */
  r0 = r0 + r1;                           /* 080EEF42 */
  r0 = *(volatile DbaaU32 *)(r0);         /* 080EEF44 */
  r1 = *(volatile DbaaU8 *)(r7 + 0x4u);   /* 080EEF46 */
  r1 = r1 << 0x5u;                        /* 080EEF48 */
  r0 = *(volatile DbaaU32 *)(r0 + 0x10u); /* 080EEF4A */
  r0 = r0 + r1;                           /* 080EEF4C */
  r1 = *(volatile DbaaU8 *)(r7 + 0x5u);   /* 080EEF4E */
  r1 = r1 << 0x1Cu;                       /* 080EEF50 */
  r1 = r1 >> 0x18u;                       /* 080EEF52 */
  __asm__("" : : "r"(r1));
  r2 = *(volatile DbaaU8 *)(r7 + 0x6u);                     /* 080EEF54 */
  r2 = r2 << 0x4u;                                          /* 080EEF56 */
  Func_08114668((const void *)r0, (DbaaU8)r1, (DbaaU16)r2); /* 080EEF58 */
  goto L_080EEFA0;                                          /* 080EEF5C */
L_080EEF6C:
  r2 = 0x40000D4u;  /* 080EEF6C */
  r1 = 0x0882323Cu; /* 080EEF6E */
  __asm__("" : : "r"(r1));
  r5 = stack[1];                          /* 080EEF70 */
  r0 = r5 << 0x2u;                        /* 080EEF72 */
  r0 = r0 + r1;                           /* 080EEF74 */
  r0 = *(volatile DbaaU32 *)(r0);         /* 080EEF76 */
  r1 = *(volatile DbaaU8 *)(r7 + 0x4u);   /* 080EEF78 */
  r1 = r1 << 0x5u;                        /* 080EEF7A */
  r0 = *(volatile DbaaU32 *)(r0 + 0x10u); /* 080EEF7C */
  r0 = r0 + r1;                           /* 080EEF7E */
  *(volatile DbaaU32 *)(r2) = r0;         /* 080EEF80 */
  r0 = *(volatile DbaaU8 *)(r7 + 0x5u);   /* 080EEF82 */
  r0 = r0 << 0x5u;                        /* 080EEF84 */
  r1 = 0x03003D10u;                       /* 080EEF86 */
  r0 = r0 + r1;                           /* 080EEF88 */
  *(volatile DbaaU32 *)(r2 + 0x4u) = r0;  /* 080EEF8A */
  r0 = *(volatile DbaaU8 *)(r7 + 0x6u);   /* 080EEF8C */
  r0 = r0 << 0x4u;                        /* 080EEF8E */
  r1 = 0x80u;                             /* 080EEF90 */
  r1 = r1 << 0x18u;                       /* 080EEF92 */
  r0 = r0 | r1;                           /* 080EEF94 */
  *(volatile DbaaU32 *)(r2 + 0x8u) = r0;  /* 080EEF96 */
  r0 = *(volatile DbaaU32 *)(r2 + 0x8u);  /* 080EEF98 */
  r0 = 0x1u;                              /* 080EEF9A */
  r3 = r3 | r0;                           /* 080EEF9C */
  *(volatile DbaaU32 *)(r4) = r3;         /* 080EEF9E */
L_080EEFA0:
  r1 = 0x03003D10u;                      /* 080EEFA0 */
  r0 = 0x0u;                             /* 080EEFA2 */
  *(volatile DbaaU16 *)(r1) = r0;        /* 080EEFA4 */
  r2 = 0x03002BA0u;                      /* 080EEFA6 */
  r0 = *(volatile DbaaU32 *)(r2);        /* 080EEFA8 */
  r1 = 0x1u;                             /* 080EEFAA */
  r0 = r0 | r1;                          /* 080EEFAC */
  *(volatile DbaaU32 *)(r2) = r0;        /* 080EEFAE */
  r0 = 0x03003BF0u;                      /* 080EEFB0 */
  r1 = stack[2];                         /* 080EEFB2 */
  r2 = r1 + r0;                          /* 080EEFB4 */
  r1 = *(volatile DbaaU16 *)(r7 + 0x8u); /* 080EEFB6 */
  *(volatile DbaaU16 *)(r2) = r1;        /* 080EEFB8 */
  r0 = r0 + 0x2u;                        /* 080EEFBA */
  r2 = stack[2];                         /* 080EEFBC */
  r0 = r2 + r0;                          /* 080EEFBE */
  r1 = *(volatile DbaaU16 *)(r7 + 0xAu); /* 080EEFC0 */
  *(volatile DbaaU16 *)(r0) = r1;        /* 080EEFC2 */
L_080EEFC4:
  return;
}
