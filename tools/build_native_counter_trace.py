"""Attach a passive counter-write log to a selected, fully hashed native build."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists()
    binary = out / 'bin'
    binary.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    label = lambda p: str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)
    path = args.baseline.resolve()
    base = json.loads(path.read_text())
    for key in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in base[key].items()), key
    old_command = base['compile']['runtime']['command']
    gcc = Path(old_command[0])
    source = ROOT / 'tools/native_counter_trace.c'
    command = [*old_command[:old_command.index('-c')], '-Wall', '-Wextra', '-Werror',
               '-c', str(source), '-o', str(binary / 'trace.o')]
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command)+'\n'+result.stdout+result.stderr)
    assert not result.returncode, result.stderr
    objects = []
    for name in base['objects_sha256']:
        p = ROOT / name
        if p.name == 'runtime.o':
            target = binary / 'runtime_traced.o'
            subprocess.run([str(gcc.with_name('objcopy.exe')), '--redefine-sym',
                            'bus_write32=Dbaa_UntracedWrite32', str(p), str(target)], check=True)
            p = target
        objects.append(p)
    objects.append(binary / 'trace.o')
    executable = binary / 'dbaa_game.exe'
    command = [str(gcc), *map(str, objects), '-Wl,--stack,16777216', '-o', str(executable),
               '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'link.log').write_text(json.dumps(command)+'\n'+result.stdout+result.stderr)
    assert not result.returncode, result.stderr
    proof = dict(base)
    proof.update(executable_sha256=sha(executable), counter_writes_logged=True, guest_write_values_changed=False,
                 clean_source_build=False, historical_objects_reused=True,
                 objects_sha256={label(p): sha(p) for p in objects}, baseline_sha256=sha(path),
                 counter_trace_source_sha256=sha(source), counter_trace_builder_sha256=sha(__file__))
    (out / 'build.json').write_text(json.dumps(proof, indent=2)+'\n')
    (out / 'trace_source.c').write_bytes(source.read_bytes())
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    print('Built passive native game-counter trace')


if __name__ == '__main__':
    main()
