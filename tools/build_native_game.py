"""Compile the Windows game from locally generated C and pinned source dependencies.

No object from the experimental build/next milestones is read or linked.
The generated C and the ROM are local inputs, not distribution artifacts.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
MGBA_PIN = 'fd9dc5c2cbf234365068855851107e762fc6211b'
FORBIDDEN = ['run_iwram_function_', 'ARMRun', 'ARMStep', 'ARMCore',
             'SM83Run', 'SM83Tick', 'GBACoreCreate', 'GBCoreCreate']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generation', type=Path, default=ROOT / 'build/windows_native_generation/generation.json')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/windows_native')
    parser.add_argument('--rom', type=Path, default=ROOT / 'baserom.gba')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    assert 1 <= args.jobs <= 8
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    relative = lambda p: str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)
    generation = args.generation.resolve()
    manifest = json.loads(generation.read_text())
    source_dir = Path(manifest['source_directory'])
    generated = Path(manifest['generated_directory'])
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    assert sha(gcc) == manifest['compiler_sha256']
    assert all(sha(source_dir / p) == h for p, h in manifest['generated_files_sha256'].items())
    assert all(sha(ROOT / p) == h for p, h in manifest['source_inputs_sha256'].items())
    rom = args.rom.resolve()
    assert hashlib.sha1(rom.read_bytes()).hexdigest() == manifest['rom_sha1']
    mgba = ROOT / 'tools/local/mgba_reference'
    assert subprocess.check_output(['git', '-C', str(mgba), 'rev-parse', 'HEAD'], text=True).strip() == MGBA_PIN
    upstream = ROOT / 'tools/local/sp00nz_gbarecomp'
    output = args.out_dir.resolve()
    objects, binary = output / 'objects', output / 'bin'
    objects.mkdir(parents=True, exist_ok=True)
    binary.mkdir(exist_ok=True)
    includes = [generated, source_dir, ROOT / 'port/include', ROOT / 'port/native', ROOT / 'port/windows']
    common = ['-std=c11', '-DGBA_NO_SDL', '-DGBA_NATIVE_ONLY', '-DGBA_WIN32_NATIVE',
              '-DDBAA_GAME_AUDIO_ENABLED', *['-I' + str(p) for p in includes]]
    jobs = []
    for name in manifest['base_sources'] + manifest['extra_sources']:
        source = Path(name)
        flags = [*common, '-O0', '-include', manifest['weak_header']]
        if source.name == 'game_entry.c':
            flags += ['-Dmain=dbaa_generated_main']
        if source == Path(manifest['background_definition_source']):
            flags += ['-Dfunc_0810DDCC=dbaa_generated_background_queue']
        jobs.append((source.stem, source, flags))
    custom = {
        'runtime': upstream / 'src/runtime.c',
        'display': upstream / 'src/display.c',
        'native_bridge': ROOT / 'port/windows/game_bridge.c',
        'native_window': ROOT / 'port/windows/game_window_async.c',
        'native_irq': ROOT / 'port/native/irq_dispatch.c',
        'native_helpers': ROOT / 'port/audio/audio_helpers.c',
        'native_player': ROOT / 'port/audio/music_player_update.c',
        'native_audio_runtime': ROOT / 'port/native/audio_runtime.c',
        'game_audio': ROOT / 'port/windows/game_audio.c',
        'digital_mixer': ROOT / 'port/audio/digital_mixer.c',
        'wasapi_sink': ROOT / 'port/windows/wasapi_sink.c',
        'save_storage': ROOT / 'port/windows/save_storage.c',
    }
    for name, source in custom.items():
        flags = [*common, '-O2']
        if name not in ['runtime', 'display']:
            flags += ['-Wall', '-Wextra', '-Werror']
        jobs.append((name, source, flags))
    chip = {
        'psg': ROOT / 'port/audio/psg_mgba.c',
        'chip': mgba / 'src/gb/audio.c',
        'timing': mgba / 'src/core/timing.c',
        'sync': mgba / 'src/core/sync.c',
        'audio_buffer': mgba / 'src/util/audio-buffer.c',
        'circle_buffer': mgba / 'src/util/circle-buffer.c',
    }
    chip_flags = ['-std=c11', '-O2', '-fwrapv', '-ffunction-sections', '-fdata-sections',
                  '-DBUILD_STATIC', '-D_GNU_SOURCE', '-D_FILE_OFFSET_BITS=64',
                  *['-I' + str(p) for p in [ROOT / 'port/third_party', mgba / 'include',
                                           mgba / 'src', ROOT / 'port/include']]]
    jobs += [(name, source, chip_flags) for name, source in chip.items()]
    assert len({n for n, s, f in jobs}) == len(jobs)
    headers = set(generated.rglob('*.h')) | set((ROOT / 'port').rglob('*.h')) | set((mgba / 'include').rglob('*.h'))
    headers.add(source_dir / 'audio_weak.h')
    headers.add(source_dir / 'game_extra_entries.inc')
    headers.add(ROOT / 'port/windows/game_audio_entries.inc')
    source_hashes = {relative(p): sha(p) for n, p, f in jobs}
    header_hashes = {relative(p): sha(p) for p in sorted(headers)}
    shared_key = hashlib.sha256(json.dumps(dict(headers=header_hashes, compiler=sha(gcc)), sort_keys=True).encode()).hexdigest()

    def compile_one(job):
        name, source, flags = job
        obj = objects / (name + '.o')
        command = [str(gcc), *flags, '-c', str(source), '-o', str(obj)]
        cache = objects / (name + '.cache.json')
        key = hashlib.sha256(json.dumps([shared_key, source_hashes[relative(source)], command]).encode()).hexdigest()
        before = time.monotonic()
        if obj.exists() and cache.exists():
            old = json.loads(cache.read_text())
            if old == dict(key=key, object=sha(obj)):
                return name, dict(returncode=0, command=command, seconds=time.monotonic() - before, cached=True)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (objects / (name + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        if result.returncode == 0:
            cache.write_text(json.dumps(dict(key=key, object=sha(obj))))
        return name, dict(returncode=result.returncode, command=command, seconds=time.monotonic() - before, cached=False)

    results = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(compile_one, job) for job in jobs]):
            name, row = future.result()
            results[name] = row
            print(name, row['returncode'], round(row['seconds'], 3), 'cached' if row['cached'] else 'compiled', flush=True)
    assert all(row['returncode'] == 0 for row in results.values()), [n for n, r in results.items() if r['returncode']]
    inputs = [objects / (name + '.o') for name, source, flags in jobs]
    executable = binary / 'dbaa_game.exe'
    link = [str(gcc), *map(str, inputs), '-Wl,--stack,16777216', '-o', str(executable),
            '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    result = subprocess.run(link, cwd=ROOT, capture_output=True, text=True)
    (binary / 'link.log').write_text(json.dumps(link) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    symbols = subprocess.check_output([str(gcc.with_name('nm.exe')), str(executable)], text=True)
    assert not any(n in symbols for n in FORBIDDEN), 'CPU interpreter linked'
    assert 'Dbaa_GameAudioAdvance' in symbols and 'Dbaa_WasapiOpen' in symbols
    (binary / 'symbols.txt').write_text(symbols)
    assert all(sha(ROOT / p) == h for p, h in source_hashes.items()), 'source changed during build'
    assert all(sha(ROOT / p) == h for p, h in header_hashes.items()), 'header changed during build'
    proof = dict(game_audio_connected=True, native_only=True, native_cpu_core_linked=False,
                 games_mmcss_requested=True, historical_objects_reused=False,
                 clean_source_build=True, game_boot_validated=False, whole_game_validated=False,
                 gba_byte_matching=False, generation_manifest=str(generation),
                 generation_manifest_sha256=sha(generation), compiler_sha256=sha(gcc),
                 builder_sha256=sha(__file__), mgba_commit=MGBA_PIN, compile=results,
                 sources_sha256=source_hashes, headers_sha256=header_hashes,
                 objects_sha256={relative(p): sha(p) for p in inputs},
                 executable_sha256=sha(executable), link_command=link)
    (output / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    sandbox = output / 'sandbox'
    sandbox.mkdir(exist_ok=True)
    target = sandbox / 'baserom.gba'
    if target.exists():
        assert sha(target) == sha(rom)
    else:
        shutil.copyfile(rom, target)
    print('Built native Windows game from source:', executable, flush=True)


if __name__ == '__main__':
    main()
