"""Compare actual native video interrupt-request gates with mGBA event hardware."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-stage', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--expect-failure', action='store_true')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    stage = args.game_stage.resolve()
    build = json.loads((stage / 'build.json').read_text())
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in build[field].items()), field
    flags = build['compile']['runtime']['command']
    gcc = Path(flags[0])
    native = ROOT / 'tools/native_video_irq_probe.c'
    oracle = ROOT / 'tools/video_irq_oracle.c'
    (out / 'native_source.c').write_bytes(native.read_bytes())
    (out / 'oracle_source.c').write_bytes(oracle.read_bytes())
    (out / 'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    objects = []
    for name in build['objects_sha256']:
        p = ROOT / name
        if p.name == 'native_bridge.o':
            target = out / 'bridge_probe.o'
            subprocess.run([str(gcc.with_name('objcopy.exe')), '--redefine-sym', 'main=Dbaa_UnusedGameMain', str(p), str(target)], check=True)
            p = target
        objects.append(p)
    mgba = ROOT / 'tools/local/mgba_reference'
    reference = ROOT / 'build/next/psg_reference/mgba_build'
    definitions = ['BUILD_STATIC', 'ENABLE_DIRECTORIES', 'ENABLE_VFS', 'ENABLE_VFS_FD',
                   'M_CORE_GB', 'M_CORE_GBA', '_GNU_SOURCE', '_FILE_OFFSET_BITS=64']
    commands = [
        [*flags[:flags.index('-c')], '-Wall', '-Wextra', '-Werror', str(native), *map(str, objects),
         '-Wl,--stack,16777216', '-o', str(out / 'native.exe'), '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt'],
        [str(gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', *['-D'+n for n in definitions],
         *['-I'+str(p) for p in [mgba/'include', reference/'include', mgba/'src']], str(oracle),
         str(reference/'libmgba.a'), '-o', str(out/'oracle.exe'), '-lws2_32', '-lshlwapi', '-lm', '-lole32', '-luuid']]
    for i, command in enumerate(commands):
        r = subprocess.run(command, capture_output=True, text=True)
        (out / f'build_{i}.log').write_text(json.dumps(command)+'\n'+r.stdout+r.stderr)
        assert not r.returncode, r.stderr
    symbols = subprocess.check_output([str(gcc.with_name('nm.exe')), str(out/'native.exe')], text=True)
    assert not any(n in symbols for n in ['ARMRun', 'ARMStep', 'ARMCore', 'GBACoreCreate', 'run_iwram_function_'])
    sandbox = out/'sandbox'
    sandbox.mkdir(); shutil.copyfile(ROOT/'baserom.gba', sandbox/'probe.gba')
    env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0', DBAA_GAME_AUDIO_REPORT=str(out/'audio.json'))
    env.pop('DBAA_GAME_PCM', None)
    cases, failures = [], []
    for mode in range(14):
        results = {}
        for name in ['native', 'oracle']:
            command = [str(out/(name+'.exe')), str(sandbox/'probe.gba'), str(mode)]
            r = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True, timeout=30)
            (out/f'{name}_{mode}.log').write_text(r.stdout+r.stderr)
            assert not r.returncode, (name, mode, r.returncode, r.stderr[-1200:])
            results[name] = list(map(int, r.stdout.strip().splitlines()[-1].split()))
        cases.append(dict(mode=mode, **results))
        if results['native'] != results['oracle']:
            failures.append(cases[-1])
    report = dict(cases=14, mismatches=len(failures), first_failures=failures,
                  results=cases, flags_equal=not failures, interrupt_enable_registers_disabled=True,
                  guest_game_instructions_executed=False, reference_cpu_instructions_executed=False,
                  native_cpu_interpreter_linked=False, cycle_timing_compared=False, whole_game_validated=False,
                  baseline_sha256=sha(stage/'build.json'), tool_sha256=sha(__file__),
                  native_source_sha256=sha(native), oracle_source_sha256=sha(oracle),
                  reference_library_sha256=sha(reference/'libmgba.a'))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    assert bool(failures) == args.expect_failure, failures
    print('PASS' if not failures else 'EXPECTED OLD RUNTIME FAILURE', 'video IRQ request gates;', len(failures), 'differences')


if __name__ == '__main__':
    main()
