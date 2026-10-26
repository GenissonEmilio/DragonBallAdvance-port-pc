"""Generate native translation sources from the user's exact local USA ROM.

Generated functions and address hints are not GBA matching proofs. This step
does not compile a game or reuse any historical game objects.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
from discover_native_entries import discover, ROM_SHA1, CODE_END

ROOT = Path(__file__).resolve().parents[1]
PIN = 'ac1176f467cbb708f58785e65f36b4f091a8ab20'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT / 'baserom.gba')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/windows_native_generation')
    args = parser.parse_args()
    rom = args.rom.resolve()
    data = rom.read_bytes()
    assert len(data) == 0x1000000 and hashlib.sha1(data).hexdigest() == ROM_SHA1, 'requires USA BDVE rev0 ROM'
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    upstream = ROOT / 'tools/local/sp00nz_gbarecomp'
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    assert gcc.is_file() and (upstream / 'src/main.c').is_file(), 'native toolchain/dependency checkout is missing'
    head = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == PIN, 'unexpected translator revision'
    patch = ROOT / 'tools/patches/gbarecomp-native.patch'
    subprocess.run(['git', '-C', str(upstream), 'apply', '--reverse', '--check', str(patch)], check=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    relative = lambda p: str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)
    translation_sources = [upstream / 'src' / (n + '.c') for n in ['rom', 'arm', 'thumb', 'disasm', 'analysis', 'translate']]
    inputs = [*translation_sources, upstream / 'src/main.c', upstream / 'src/runtime.c', upstream / 'src/display.c',
              *sorted((upstream / 'include').rglob('*.h')), ROOT / 'tools/native_emit_extensions.c',
              ROOT / 'tools/discover_native_entries.py', Path(__file__), patch,
              ROOT / 'config/functions.usa.json', ROOT / 'config/assembly.usa.json',
              ROOT / 'port/windows/game_audio_entries.inc']
    hashes = {relative(p): sha(p) for p in inputs}
    key = hashlib.sha256(json.dumps(dict(rom=ROM_SHA1, compiler=sha(gcc), inputs=hashes), sort_keys=True).encode()).hexdigest()
    work = out / ('sources-' + key[:16])
    manifest = work / 'generation.json'
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        assert previous['input_key'] == key
        assert all(sha(work / p) == h for p, h in previous['generated_files_sha256'].items())
        (out / 'generation.json').write_text(json.dumps(previous, indent=2) + '\n')
        print('Verified existing generated sources:', work)
        return
    assert not work.exists(), 'incomplete generation exists; select a fresh output directory'
    work.mkdir()
    generated = work / 'generated'
    generated.mkdir()
    tools = work / 'tools'
    tools.mkdir()
    def run(name, command, cwd=ROOT, env=None):
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, capture_output=True, text=True)
        (work / (name + '.log')).write_text(json.dumps(list(map(str, command))) + '\n' + result.stdout + result.stderr)
        assert result.returncode == 0, (name, result.stderr[-2000:])
    common = [str(gcc), '-std=c11', '-O2', '-I' + str(upstream / 'include')]
    run('build_translator', [*common, upstream / 'src/main.c', *translation_sources, '-o', tools / 'gbarecomp.exe'])
    run('build_extensions', [*common, ROOT / 'tools/native_emit_extensions.c', *translation_sources,
                             '-o', tools / 'emit_extensions.exe'])
    # Preserve the seed contract of the exercised translation: matching
    # function/assembly addresses are Thumb analysis hints here. Their actual
    # GBA instruction mode and matching remain checked by separate manifests.
    functions = json.loads((ROOT / 'config/functions.usa.json').read_text())['functions']
    assembly = json.loads((ROOT / 'config/assembly.usa.json').read_text())['functions']
    seeds = [int(t['address'], 0) | 1 for t in [*functions, *assembly]]
    seed_file = work / 'base_entries.txt'
    seed_file.write_text(''.join(f'0x{a:08X}\n' for a in seeds))
    env = dict(os.environ, GBA_CODE_END=hex(CODE_END), GBA_STRICT_FALLTHROUGH='1')
    run('translate', [tools / 'gbarecomp.exe', 'translate', rom, '-o', generated, '--multi',
                      '--entries', seed_file], cwd=upstream, env=env)
    header = generated / 'game.h'
    pointers, missing, tables = discover(data, header.read_text())
    extra_file = work / 'extra_entries.txt'
    combined = sorted(set(pointers) | set(missing))
    extra_file.write_text(''.join(f'0x{a:08X}\n' for a in combined))
    run('emit_extensions', [tools / 'emit_extensions.exe', rom, seed_file, extra_file, header,
                            work / 'game_extra.c', work / 'game_extra_entries.inc'], env=env)
    addresses = {int(a, 16) for a in re.findall(r'DBAA_AUDIO_ENTRY\(([0-9A-F]+),',
                                               (ROOT / 'port/windows/game_audio_entries.inc').read_text())}
    addresses.add(0x0810A6D8)
    weak = ['#ifndef DBAA_NATIVE_AUDIO_WEAK_H', '#define DBAA_NATIVE_AUDIO_WEAK_H',
            *[f'void func_{a:08X}(void) __attribute__((weak));' for a in sorted(addresses)],
            'void cpu_bx(unsigned target) __attribute__((weak));',
            'void func_07FFFC30(void) __attribute__((weak));', '#endif']
    (work / 'audio_weak.h').write_text('\n'.join(weak) + '\n')
    base_units = [*sorted(generated.glob('funcs_*.c')), *sorted(generated.glob('stubs_*.c')),
                  generated / 'game_entry.c']
    background = [p for p in base_units if 'void func_0810DDCC(void) {' in p.read_text()]
    assert len(background) == 1, 'background wrapper definition is ambiguous'
    extra_units = [Path(p) for p in (work / 'game_extra_sources.txt').read_text().splitlines()]
    files = [*generated.rglob('*.c'), *generated.rglob('*.h'), *work.glob('game_extra*'),
             work / 'base_entries.txt', extra_file, work / 'audio_weak.h']
    files = sorted({p for p in files if p.is_file()})
    report = dict(input_key=key, rom_sha1=ROM_SHA1, upstream_commit=PIN, compiler_sha256=sha(gcc),
                  source_inputs_sha256=hashes, source_directory=str(work),
                  generated_directory=str(generated), base_sources=[str(p) for p in base_units],
                  extra_sources=[str(p) for p in extra_units], weak_header=str(work / 'audio_weak.h'),
                  background_definition_source=str(background[0]),
                  seed_entries=len(seeds), pointer_candidates=len(pointers), tables=len(tables),
                  table_candidates=len(missing), combined_extra_candidates=len(combined),
                  generated_candidate_functions=len(re.findall(r'void func_[0-9A-F]+\(void\)', header.read_text())),
                  generated_files_sha256={str(p.relative_to(work)): sha(p) for p in files},
                  gba_byte_matching=False, game_compiled=False, generated_sources_manually_patched=False)
    manifest.write_text(json.dumps(report, indent=2) + '\n')
    (out / 'generation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Generated native sources from the local ROM:', work)


if __name__ == '__main__':
    main()
