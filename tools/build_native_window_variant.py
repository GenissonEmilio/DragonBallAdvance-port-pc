"""Isolate a window backend change against a source-built native game."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'build/windows_native')
    parser.add_argument('--source', type=Path, default=ROOT / 'port/windows/game_window_async.c')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/windows_native_async')
    args = parser.parse_args()
    stage, out = args.baseline.resolve(), args.out_dir.resolve()
    assert not out.exists(), 'use a new output directory'
    binary = out / 'bin'
    binary.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    label = lambda p: str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)
    baseline = json.loads((stage / 'build.json').read_text())
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in baseline[field].items()), field
    source = args.source.resolve()
    command = list(baseline['compile']['native_window']['command'])
    original = Path(command[command.index('-c') + 1])
    command[command.index('-c') + 1] = str(source)
    command[command.index('-o') + 1] = str(binary / 'native_window.o')
    r = subprocess.run(command, capture_output=True, text=True)
    (binary / 'native_window.log').write_text(json.dumps(command) + '\n' + r.stdout + r.stderr)
    assert r.returncode == 0, r.stderr
    objects = [binary / 'native_window.o' if Path(p).name == 'native_window.o' else ROOT / p
               for p in baseline['objects_sha256']]
    link = [command[0], *map(str, objects), '-Wl,--stack,16777216', '-o', str(binary / 'dbaa_game.exe'),
            '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    r = subprocess.run(link, capture_output=True, text=True)
    (binary / 'link.log').write_text(json.dumps(link) + '\n' + r.stdout + r.stderr)
    assert r.returncode == 0, r.stderr
    proof = dict(baseline)
    proof['sources_sha256'] = dict(baseline['sources_sha256'])
    proof['sources_sha256'].pop(label(original))
    proof['sources_sha256'][label(source)] = sha(source)
    proof['compile'] = dict(baseline['compile'])
    proof['compile']['native_window'] = dict(command=command, returncode=0, cached=False)
    proof.update(executable_sha256=sha(binary / 'dbaa_game.exe'), window_variant=True,
                 baseline_sha256=sha(stage / 'build.json'), builder_sha256=sha(__file__),
                 objects_sha256={label(p): sha(p) for p in objects}, link_command=link)
    (out / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    print('Built isolated window backend:', binary / 'dbaa_game.exe')


if __name__ == '__main__':
    main()
