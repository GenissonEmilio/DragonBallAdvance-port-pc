"""Build only mGBA's native PSG chip, without its ARM or SM83 CPU cores."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = 'fd9dc5c2cbf234365068855851107e762fc6211b'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path,
                        default=ROOT / 'build/native_psg')
    parser.add_argument('--source', type=Path, default=ROOT / 'port/audio/psg_mgba.c')
    args = parser.parse_args(argv)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    upstream = ROOT / 'tools/local/mgba_reference'
    configured = ROOT / 'build/next/psg_reference/mgba_build/include'
    compiler = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    flags = out / 'include/mgba/flags.h'
    flags.parent.mkdir(parents=True, exist_ok=True)
    # All struct feature flags match the configured reference except CPU cores.
    # Their removal makes the PSG's unused core callbacks inert; no source file
    # is changed, and the adapter drives the chip's frame sequencer itself.
    text = (configured / 'mgba/flags.h').read_text()
    for name in ['M_CORE_GBA', 'M_CORE_GB']:
        assert text.count('#define ' + name + '\n') == 1
        text = text.replace('#define ' + name + '\n', '/* standalone PSG: ' + name + ' disabled */\n')
    flags.write_text(text)
    sources = {
        'psg': args.source.resolve(),
        'chip': upstream / 'src/gb/audio.c',
        'timing': upstream / 'src/core/timing.c',
        'sync': upstream / 'src/core/sync.c',
        'audio_buffer': upstream / 'src/util/audio-buffer.c',
        'circle_buffer': upstream / 'src/util/circle-buffer.c',
    }
    includes = [out / 'include', upstream / 'include', configured,
                upstream / 'src', ROOT / 'port/include']
    commands = []
    for name, source in sources.items():
        command = [str(compiler), '-std=c11', '-O2', '-fwrapv',
                   '-ffunction-sections', '-fdata-sections', '-DBUILD_STATIC',
                   '-D_GNU_SOURCE', '-D_FILE_OFFSET_BITS=64',
                   *['-I' + str(p) for p in includes], '-c', str(source),
                   '-o', str(out / (name + '.o'))]
        result = subprocess.run(command, capture_output=True, text=True)
        (out / (name + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        if result.returncode:
            print(result.stderr)
            return 1
        commands.append(command)
    exports = ['Create', 'Destroy', 'Advance', 'Write', 'Status', 'Sample']
    (out / 'psg.def').write_text('EXPORTS\n' + '\n'.join('Dbaa_Psg' + n for n in exports) + '\n')
    command = [str(compiler), '-shared', *[str(out / (n + '.o')) for n in sources],
               str(out / 'psg.def'), '-Wl,--gc-sections,--exclude-all-symbols',
               '-o', str(out / 'psg.dll')]
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'link.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    if result.returncode:
        print(result.stderr)
        return 1
    commands.append(command)
    symbols = subprocess.check_output([str(compiler.with_name('nm.exe')), str(out / 'psg.dll')], text=True)
    forbidden = ['ARMRun', 'ARMStep', 'ARMCore', 'SM83Run', 'SM83Tick', 'GBACoreCreate', 'GBCoreCreate']
    assert not any(n in symbols for n in forbidden), 'CPU symbols linked into standalone PSG'
    (out / 'symbols.txt').write_text(symbols)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report = dict(upstream_commit=PIN, cpu_core_macros_enabled=False,
                  cpu_cores_linked=False, gba_byte_matching=False,
                  compiler_sha256=sha(compiler),
                  sources_sha256={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p) for p in sources.values()},
                  configuration_sha256=sha(flags), commands=commands,
                  builder_sha256=sha(__file__),
                  headers_sha256={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p)
                                  for p in sorted(set((upstream / 'include').rglob('*.h')) |
                                                  set(configured.rglob('*.h')) |
                                                  {ROOT / 'port/include/psg.h', flags})},
                  objects_sha256={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p)
                                  for p in [out / (name + '.o') for name in sources]},
                  library_sha256=sha(out / 'psg.dll'))
    (out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Built standalone native PSG:', out / 'psg.dll')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
