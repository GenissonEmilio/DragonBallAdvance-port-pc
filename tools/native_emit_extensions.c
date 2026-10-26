/* Emit additional statically discovered functions with the pinned translator.
 * Existing generated units are immutable inputs; no C output is patched. */
#include "gba/analysis.h"
#include "gba/rom.h"
#include "gba/translate.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static u32 known[65536];
static unsigned count;
static int present(u32 address) {
  for (unsigned i = 0; i < count; ++i)
    if (known[i] == address)
      return 1;
  return 0;
}
int main(int argc, char **argv) {
  if (argc != 7) {
    fprintf(stderr, "usage: emit rom seed_entries extra_entries base_game.h "
                    "output.c output.inc\n");
    return 2;
  }
  FILE *header = fopen(argv[4], "r");
  if (!header)
    return 1;
  char line[512];
  while (fgets(line, sizeof(line), header)) {
    unsigned address;
    if (sscanf(line, "void func_%x(void)", &address) == 1) {
      if (count == 65536)
        return 1;
      known[count++] = address;
    }
  }
  fclose(header);
  GbaRom *rom = rom_load(argv[1]);
  if (!rom)
    return 1;
  AnalysisCtx *analysis = analysis_create(rom);
  if (analysis_load_entries(analysis, argv[2]) < 0 ||
      analysis_load_entries(analysis, argv[3]) < 0)
    return 1;
  analysis_run(analysis);
  char prefix[1024], header_path[1100], list_path[1100];
  if (strlen(argv[5]) >= sizeof(prefix))
    return 1;
  strcpy(prefix, argv[5]);
  char *dot = strrchr(prefix, '.');
  if (dot)
    *dot = 0;
  snprintf(header_path, sizeof(header_path), "%s.h", prefix);
  snprintf(list_path, sizeof(list_path), "%s_sources.txt", prefix);
  FILE *output = fopen(header_path, "w"), *entries = fopen(argv[6], "w");
  FILE *sources = fopen(list_path, "w");
  if (!output || !entries || !sources)
    return 1;
  fprintf(output, "/* Generated from the local ROM; do not edit. */\n#include "
                  "\"game.h\"\n");
  unsigned emitted = 0;
  for (int i = 0; i < analysis->num_functions; ++i) {
    const Function *function = &analysis->functions[i];
    if (!present(function->entry)) {
      fprintf(output, "void func_%08X(void);\n", function->entry);
      fprintf(entries, "DBAA_GAME_ENTRY(%08X, 0x%08Xu)\n", function->entry,
              function->entry | (function->mode == CODE_THUMB ? 1u : 0u));
      ++emitted;
    }
  }
  fclose(output);
  const char *basename = strrchr(prefix, '/');
  basename = basename ? basename + 1 : prefix;
  const char *backslash = strrchr(basename, '\\');
  if (backslash)
    basename = backslash + 1;
  unsigned written = 0, shard = 0;
  TranslateCtx *translate = NULL;
  output = NULL;
  for (int i = 0; i < analysis->num_functions; ++i) {
    if (present(analysis->functions[i].entry))
      continue;
    if (written % 100 == 0) {
      if (translate)
        translate_free(translate);
      if (output)
        fclose(output);
      char source_path[1100];
      snprintf(source_path, sizeof(source_path), "%s_%03u.c", prefix, shard++);
      output = fopen(source_path, "w");
      if (!output)
        return 1;
      fprintf(sources, "%s\n", source_path);
      fprintf(output,
              "/* Generated from the local ROM; do not edit. */\n#include "
              "\"%s.h\"\n",
              basename);
      translate = translate_create(rom, analysis, output);
    }
    translate_function(translate, &analysis->functions[i]);
    ++written;
  }
  if (translate)
    translate_free(translate);
  if (output)
    fclose(output);
  fclose(sources);
  fclose(entries);
  printf("Emitted %u additional native functions\n", emitted);
  return 0;
}
