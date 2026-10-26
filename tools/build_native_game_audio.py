"""Build the actual game PCM/PSG consumer against a private test RAM bus."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GCC = ROOT / 'tools/local/w64devkit/bin/gcc.exe'


def psg_inputs(directory):
    """Reuse only the exact native chip objects that passed the hardware gate."""
    directory = Path(directory).resolve()
    proof = json.loads((directory / 'build.json').read_text())
    result = json.loads((directory / 'report.json').read_text())
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in proof[field].items()), field
    assert result['adapter_sha256'] == sha(ROOT / 'port/audio/psg_mgba.c')
    assert not result['quick']
    assert result['raw_digital_psg_equal'] and result['nr52_equal']
    assert result['soundbias_resolutions_tested'] == [0, 1, 2, 3]
    assert not proof['cpu_cores_linked'] and not proof['cpu_core_macros_enabled']
    # Names correspond to the individual sources recorded by the chip builder.
    objects = [directory / (n + '.o') for n in ['psg', 'chip', 'timing', 'sync',
                                               'audio_buffer', 'circle_buffer']]
    assert all(p.is_file() for p in objects)
    return objects, proof, result


def build(out, source=None, psg_dir=None):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    objects, chip_build, chip_report = psg_inputs(
        psg_dir or ROOT / 'build/native_psg_bias_validation')
    source = Path(source or ROOT / 'port/windows/game_audio.c').resolve()
    sources = [source, ROOT / 'port/audio/digital_mixer.c', ROOT / 'port/windows/wasapi_sink.c', ROOT / 'tools/game_audio_probe.c']
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             *['-I' + str(ROOT / p) for p in ['port/include', 'port/native', 'port/windows']]]
    exports = ['Init', 'Advance', 'Write', 'VBlank', 'Close', 'Error', 'ProbeMemory']
    (out / 'consumer.def').write_text('EXPORTS\n' + '\n'.join('Dbaa_GameAudio' + n for n in exports) + '\n')
    command = [str(GCC), *flags, '-shared', *map(str, sources), *map(str, objects),
               str(out / 'consumer.def'), '-Wl,--exclude-all-symbols',
               '-lole32', '-luuid', '-lavrt', '-o', str(out / 'consumer.dll')]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    paths = [*sources, ROOT / 'port/windows/game_audio.h', ROOT / 'port/windows/wasapi_sink.h',
             ROOT / 'port/include/psg.h', ROOT / 'port/include/digital_mixer.h', ROOT / 'port/native/audio_runtime.h']
    proof = dict(command=command, compiler_sha256=sha(GCC),
                 sources_sha256={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p) for p in paths},
                 objects_sha256={str(p.relative_to(ROOT)): sha(p) for p in objects},
                 chip_build=chip_build, chip_report=chip_report,
                 library_sha256=sha(out / 'consumer.dll'), native_cpu_core_linked=False)
    symbols = subprocess.check_output([str(GCC.with_name('nm.exe')), str(out / 'consumer.dll')], text=True)
    assert not any(n in symbols for n in ['ARMRun', 'ARMStep', 'SM83Tick', 'GBACoreCreate'])
    (out / 'symbols.txt').write_text(symbols)
    (out / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    return out / 'consumer.dll'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_game_audio_validation')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--psg-dir', type=Path)
    args = parser.parse_args(argv)
    print('Built', build(args.out_dir, args.source, args.psg_dir))


if __name__ == '__main__':
    main()
