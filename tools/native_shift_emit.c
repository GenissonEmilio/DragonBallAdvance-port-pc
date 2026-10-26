/* Emit isolated instruction probes through the actual pinned translator.
 * All instruction bytes are read from the local ROM; no game CPU is linked. */
#include "gba/translate.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  GbaRom *rom = rom_load(argv[1]);
  FILE *spec = fopen(argv[2], "r"), *out = fopen(argv[3], "w");
  if (!rom || !spec || !out) return 1;
  fprintf(out, "#include \"gba/gba_runtime.h\"\nu32 r[16]; bool CPU_N,CPU_Z,CPU_C,CPU_V;\n");
  TranslateCtx *ctx = translate_create(rom, NULL, out);
  unsigned count = 0, address;
  char mode;
  while (fscanf(spec, " %c %x", &mode, &address) == 2) {
    fprintf(out, "static void execute_%u(void) {\n", count);
    ctx->indent = 1;
    if (mode == 'T') {
      ThumbInsn instruction = thumb_decode(rom_read16(rom, address));
      translate_thumb_insn(ctx, &instruction, address);
    } else if (mode == 'A') {
      ArmInsn instruction = arm_decode(rom_read32(rom, address));
      translate_arm_insn(ctx, &instruction, address);
    } else return 3;
    fprintf(out, "}\n");
    ++count;
  }
  fprintf(out, "__declspec(dllexport) int Probe(unsigned index,const u32*in,u32 flags,u32*out){\n"
          "memcpy(r,in,sizeof(r)); CPU_N=!!(flags&0x80000000u);CPU_Z=!!(flags&0x40000000u);"
          "CPU_C=!!(flags&0x20000000u);CPU_V=!!(flags&0x10000000u);switch(index){\n");
  for (unsigned i = 0; i < count; ++i)
    fprintf(out, "case %u:execute_%u();break;\n", i, i);
  fprintf(out, "default:return 0;}memcpy(out,r,15*sizeof(u32));"
          "out[15]=(CPU_N?0x80000000u:0)|(CPU_Z?0x40000000u:0)|"
          "(CPU_C?0x20000000u:0)|(CPU_V?0x10000000u:0);return 1;}\n");
  translate_free(ctx);
  fclose(spec);
  fclose(out);
  rom_free(rom);
  return count ? 0 : 4;
}
