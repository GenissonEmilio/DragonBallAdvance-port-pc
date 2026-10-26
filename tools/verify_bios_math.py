"""Compare fixed-point BIOS registers to pinned mGBA, including old negative control."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_bios_math_validation')
    parser.add_argument('--negative-runtime', type=Path, help='optional preserved pre-fix runtime for the negative control')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve earlier evidence'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    mgba = ROOT / 'tools/local/mgba_reference'
    configured = ROOT / 'build/next/psg_reference/mgba_build'
    assert subprocess.check_output(['git', '-C', str(mgba), 'rev-parse', 'HEAD'], text=True).strip() == 'fd9dc5c2cbf234365068855851107e762fc6211b'
    header = ROOT / 'port/include/bios_math.h'
    rom = ROOT / 'baserom.gba'
    assert hashlib.sha1(rom.read_bytes()).hexdigest() == '1338584d8cfa57402603197e65d2e2ff0184d24f'
    (out / 'bios_math.h').write_bytes(header.read_bytes())
    (out / 'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    (out / 'oracle_source.c').write_bytes((ROOT / 'tools/bios_math_oracle.c').read_bytes())
    source = out / 'native.c'
    source.write_text('''#include "bios_math.h"
#include <stdio.h>
int main(int n, char **v) {
  if (n != 3) { return 2; }
  FILE *i = fopen(v[1], "rb"), *o = fopen(v[2], "wb");
  if (!i || !o) { return 1; }
  uint32_t row[5];
  while (fread(row, sizeof(row), 1, i) == 1) {
    if (row[0] == 9) { Dbaa_BiosArcTan(row+1); }
    else { Dbaa_BiosArcTan2(row+1); }
    if (fwrite(row+1, 16, 1, o) != 1) { return 1; }
  }
  int ok = !ferror(i) && feof(i);
  ok &= !fclose(i);
  ok &= !fclose(o);
  return ok ? 0 : 1;
}
''')
    # Preserve the exact old SWI case bodies and compile them as a negative
    # control. Cardinal inputs avoid the old cubic's signed overflow.
    runtime = args.negative_runtime.resolve() if args.negative_runtime else None
    old_cases = runtime.read_text().split('    case 0x09: { /* ArcTan */', 1)[1].split('    case 0x0B: /* CpuSet */', 1)[0] if runtime else ''
    old_source = out / 'old.c'
    if runtime:
        old_source.write_text('#include <stdint.h>\n#include <stdio.h>\n#include <math.h>\n'
                          'typedef int32_t s32;typedef int16_t s16;typedef uint32_t u32;typedef uint16_t u16;\n'
                          'int main(void){u32 r[4]={1,0,0x12345678,0xabcdef01};switch(10){'
                          'case 0x09: { /* ArcTan */' + old_cases + '}printf("%u\\n",r[0]);return 0;}\n')
    definitions = ['BUILD_STATIC', 'ENABLE_DIRECTORIES', 'ENABLE_VFS', 'ENABLE_VFS_FD',
                   'M_CORE_GB', 'M_CORE_GBA', '_GNU_SOURCE', '_FILE_OFFSET_BITS=64']
    commands = [[str(gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(out / 'native.exe')],
                [str(gcc), '-std=c11', '-O2', *['-D' + n for n in definitions],
                 *['-I' + str(p) for p in [mgba / 'include', configured / 'include', mgba / 'src']],
                 str(out / 'oracle_source.c'), str(configured / 'libmgba.a'), '-o', str(out / 'oracle.exe'),
                 '-lws2_32', '-lshlwapi', '-lm', '-lole32', '-luuid'],
                *([[str(gcc), '-std=c11', '-O2', str(old_source), '-o', str(out / 'old.exe'), '-lm']] if runtime else [])]
    for i, command in enumerate(commands):
        r = subprocess.run(command, capture_output=True, text=True)
        (out / f'build_{i}.log').write_text(json.dumps(command) + '\n' + r.stdout + r.stderr)
        assert not r.returncode, r.stderr
    old_cardinal = int(subprocess.check_output([str(out / 'old.exe')], text=True).strip()) if runtime else None
    if runtime:
        assert old_cardinal == 0x8000, 'negative control no longer has the observed 180-degree error'
    cases = [(9, x & 0xFFFFFFFF, 0xABCD0123, 0x56789ABC, 0xCDEF1357) for x in range(-32768, 32768)]
    values = [-32768, -32767, -16384, -8192, -256, -1, 0, 1, 2, 255, 256, 8192, 16384, 32766, 32767]
    pairs = [(x, y) for x in values for y in values]
    rng = random.Random(0xB105A7)
    pairs += [(rng.randrange(-32768, 32768), rng.randrange(-32768, 32768)) for _ in range(131072)]
    cases += [(10, x & 0xFFFFFFFF, y & 0xFFFFFFFF, 0x56789ABC, 0xCDEF1357) for x, y in pairs]
    data = b''.join(struct.pack('<5I', *row) for row in cases)
    (out / 'inputs.bin').write_bytes(data)
    for name in ['native', 'oracle']:
        command = [str(out / (name + '.exe')), str(out / 'inputs.bin'), str(out / (name + '.bin'))]
        if name == 'oracle':
            command.append(str(rom))
        r = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (out / (name + '.log')).write_text(r.stdout + r.stderr)
        assert not r.returncode, (name, r.returncode, r.stderr)
    expected, actual = [(out / (name + '.bin')).read_bytes() for name in ['oracle', 'native']]
    assert len(expected) == len(actual) == len(cases) * 16
    mismatches = [i for i in range(len(cases)) if actual[i*16:(i+1)*16] != expected[i*16:(i+1)*16]]
    report = dict(cases=len(cases), arctan_cases=65536, arctan2_cases=len(pairs),
                  all_int16_arctan_inputs=True, registers_compared=['r0', 'r1', 'r2', 'r3'],
                  mismatches=len(mismatches), registers_equal=not mismatches,
                  first_differences=[dict(input=cases[i], native=struct.unpack_from('<4I', actual, 16*i),
                                          reference=struct.unpack_from('<4I', expected, 16*i)) for i in mismatches[:16]],
                  old_arctan2_positive_x_axis=old_cardinal, expected_positive_x_axis=0,
                  native_cpu_interpreter_linked=False, software_bios_reference=True,
                  physical_bios_compared=False, cycles_compared=False, whole_game_validated=False,
                  header_sha256=sha(header), tool_sha256=sha(__file__), compiler_sha256=sha(gcc),
                  oracle_source_sha256=sha(ROOT / 'tools/bios_math_oracle.c'),
                  reference_library_sha256=sha(configured / 'libmgba.a'), old_runtime_sha256=sha(runtime) if runtime else None,
                  expected_sha256=hashlib.sha256(expected).hexdigest(), actual_sha256=hashlib.sha256(actual).hexdigest())
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    assert not mismatches, report['first_differences'][:1]
    print('PASS BIOS math:', len(cases), 'cases, r0-r3 exact;', 'old cardinal defect reproduced' if runtime else 'negative control omitted')


if __name__ == '__main__':
    main()
