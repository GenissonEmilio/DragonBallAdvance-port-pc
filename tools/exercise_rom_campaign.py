"""Observe the original USA ROM with ordinary input; no native parity assumption."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import struct
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--save', type=Path)
    parser.add_argument('--frames', type=int, default=6000)
    parser.add_argument('--controller', action='store_true', help='read-only observations choose ordinary buttons')
    parser.add_argument('--trace-swis', help='optional inclusive frame range, e.g. 1780,1820')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve earlier evidence'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rom = ROOT / 'baserom.gba'
    assert hashlib.sha1(rom.read_bytes()).hexdigest() == '1338584d8cfa57402603197e65d2e2ff0184d24f'
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    mgba = ROOT / 'tools/local/mgba_reference'
    configured = ROOT / 'build/next/psg_reference/mgba_build'
    assert subprocess.check_output(['git', '-C', str(mgba), 'rev-parse', 'HEAD'], text=True).strip() == 'fd9dc5c2cbf234365068855851107e762fc6211b'
    source = ROOT / 'tools/game_campaign_oracle.c'
    (out / 'oracle_source.c').write_bytes(source.read_bytes())
    (out / 'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    (out / 'input.txt').write_bytes(args.input.read_bytes())
    definitions = ['BUILD_STATIC', 'ENABLE_DIRECTORIES', 'ENABLE_VFS', 'ENABLE_VFS_FD',
                   'M_CORE_GB', 'M_CORE_GBA', '_GNU_SOURCE', '_FILE_OFFSET_BITS=64']
    if args.controller:
        definitions.append('DBAA_TEST_CONTROLLER')
        (out / 'controller_source.h').write_bytes((ROOT / 'tools/campaign_controller.h').read_bytes())
    command = [str(gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
               *['-D' + n for n in definitions],
               *['-I' + str(p) for p in [mgba / 'include', configured / 'include', mgba / 'src']],
               str(source), str(configured / 'libmgba.a'), '-o', str(out / 'oracle.exe'),
               '-lws2_32', '-lshlwapi', '-lm', '-lole32', '-luuid']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert not result.returncode, result.stderr
    command = [str(out / 'oracle.exe'), str(rom), str(args.frames), str(out / 'input.txt'),
               str(out / 'observations.csv'), str(out / 'save.eep'), str(out / 'final.memory'), str(out / 'final.ppm')]
    if args.save:
        assert args.save.stat().st_size == 512
        (out / 'seed.eep').write_bytes(args.save.read_bytes())
        command.append(str(out / 'seed.eep'))
    before = time.monotonic()
    env = dict(os.environ, DBAA_ORACLE_SWI_LOG=args.trace_swis or '')
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=max(90, args.frames / 80))
    (out / 'run.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert not result.returncode, result.stderr
    reference = json.loads(result.stdout.strip().splitlines()[-1])
    assert reference['ok'] and reference['frames'] == args.frames
    # Pixel format conversion only, for the app's BMP preview support.
    ppm = (out / 'final.ppm').read_bytes().split(b'\n', 3)
    assert ppm[:3] == [b'P6', b'240 160', b'255'] and len(ppm[3]) == 240 * 160 * 3
    rgb = ppm[3]
    bgra = b''.join(bytes((rgb[i+2], rgb[i+1], rgb[i], 0)) for i in range(0, len(rgb), 3))
    header = bytearray(54)
    header[:2] = b'BM'
    struct.pack_into('<I', header, 2, len(bgra) + 54)
    struct.pack_into('<I', header, 10, 54)
    struct.pack_into('<IiiHH', header, 14, 40, 240, -160, 1, 32)
    struct.pack_into('<I', header, 34, len(bgra))
    (out / 'final.bmp').write_bytes(header + bgra)
    report = dict(reference=reference, seconds=time.monotonic()-before, command=command,
                  rom_sha1=hashlib.sha1(rom.read_bytes()).hexdigest(), source_sha256=sha(source),
                  tool_sha256=sha(__file__), compiler_sha256=sha(gcc),
                  original_mgba_library_sha256=sha(configured / 'libmgba.a'),
                  ordinary_buttons_only=True, native_cpu_core_linked=False,
                  observational_controller=args.controller,
                  trace_swis=args.trace_swis,
                  native_game_parity_validated=False, campaign_completed=False,
                  files_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file()})
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Observed original USA ROM:', args.frames, 'frames;', out, flush=True)


if __name__ == '__main__':
    main()
