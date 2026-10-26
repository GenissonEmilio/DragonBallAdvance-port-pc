"""Compare the actual runtime's SWI results with the immutable math reference."""
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
    parser.add_argument('--game-stage', type=Path, default=ROOT / 'build/windows_native_shift')
    parser.add_argument('--reference', type=Path, default=ROOT / 'build/native_bios_math_validation_v4')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_bios_math_runtime_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve earlier evidence'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    baseline = args.game_stage.resolve()
    build = json.loads((baseline / 'build.json').read_text())
    reference = args.reference.resolve()
    report = json.loads((reference / 'report.json').read_text())
    header = ROOT / 'port/include/bios_math.h'
    assert report['registers_equal'] and report['mismatches'] == 0 and report['header_sha256'] == sha(header)
    assert sha(reference / 'oracle.bin') == report['expected_sha256']
    runtime = ROOT / 'tools/local/sp00nz_gbarecomp/src/runtime.c'
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(ROOT / p == runtime or sha(ROOT / p) == h for p, h in build[field].items()), field
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    assert sha(gcc) == build['compiler_sha256']
    command = list(build['compile']['runtime']['command'])
    command[command.index('-o')+1] = str(out / 'runtime.o')
    source = ROOT / 'tools/native_bios_math_probe.c'
    command_probe = [*command[:command.index('-c')], '-Wall', '-Wextra', '-Werror', '-c', str(source), '-o', str(out / 'probe.o')]
    for i, row in enumerate([command, command_probe]):
        r = subprocess.run(row, capture_output=True, text=True)
        (out / f'build_{i}.log').write_text(json.dumps(row) + '\n' + r.stdout + r.stderr)
        assert not r.returncode, r.stderr
    objects = []
    for path in build['objects_sha256']:
        p = ROOT / path
        if p.name == 'runtime.o':
            p = out / 'runtime.o'
        elif p.name == 'native_bridge.o':
            target = out / 'bridge_probe.o'
            subprocess.run([str(gcc.with_name('objcopy.exe')), '--redefine-sym', 'main=Dbaa_UnusedGameMain', str(p), str(target)], check=True)
            p = target
        objects.append(p)
    command_link = [str(gcc), str(out / 'probe.o'), *map(str, objects), '-Wl,--stack,16777216',
                    '-o', str(out / 'probe.exe'), '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    r = subprocess.run(command_link, capture_output=True, text=True)
    (out / 'link.log').write_text(json.dumps(command_link) + '\n' + r.stdout + r.stderr)
    assert not r.returncode, r.stderr
    symbols = subprocess.check_output([str(gcc.with_name('nm.exe')), str(out / 'probe.exe')], text=True)
    assert not any(s in symbols for s in ['ARMRun', 'ARMStep', 'ARMCore', 'GBACoreCreate', 'run_iwram_function_'])
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0', DBAA_GAME_AUDIO_REPORT=str(out / 'audio.json'))
    env.pop('DBAA_GAME_PCM', None)
    row = [str(out / 'probe.exe'), str(sandbox / 'baserom.gba'), str(reference / 'inputs.bin'), str(out / 'actual.bin')]
    r = subprocess.run(row, cwd=sandbox, env=env, capture_output=True, text=True, timeout=90)
    (out / 'run.log').write_text(json.dumps(row) + '\n' + r.stdout + r.stderr)
    assert not r.returncode, (r.returncode, r.stderr[-1200:])
    equal = (out / 'actual.bin').read_bytes() == (reference / 'oracle.bin').read_bytes()
    proof = dict(cases=report['cases'], runtime_swi_registers_equal=equal, registers=['r0', 'r1', 'r2', 'r3'],
                 reference_sha256=sha(reference / 'oracle.bin'), actual_sha256=sha(out / 'actual.bin'),
                 runtime_source_sha256=sha(runtime), header_sha256=sha(header), tool_sha256=sha(__file__),
                 probe_source_sha256=sha(source), probe_exe_sha256=sha(out / 'probe.exe'), runtime_object_sha256=sha(out / 'runtime.o'),
                 baseline_sha256=sha(baseline / 'build.json'), reference_report_sha256=sha(reference / 'report.json'),
                 native_cpu_interpreter_linked=False, gba_byte_matching=False, full_game_boot=False, cycles_compared=False)
    (out / 'report.json').write_text(json.dumps(proof, indent=2) + '\n')
    assert equal
    print('PASS actual native runtime SWIs:', report['cases'], 'cases, r0-r3 exact')


if __name__ == '__main__':
    main()
