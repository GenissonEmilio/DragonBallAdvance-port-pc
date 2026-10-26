"""Add test-only window timing to an explicitly selected native build."""
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
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_window_profile')
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
    window = list(baseline['compile']['native_window']['command'])
    gcc = Path(window[0])
    source = ROOT / 'tools/native_window_profile.c'
    flags = window[1:window.index('-c')]
    renames = ['-DDbaa_WindowPresent=dbaa_profile_original_present',
               '-DDbaa_WindowPoll=dbaa_profile_original_poll', '-DDbaa_WindowPace=dbaa_profile_original_pace']
    window = [window[0], *flags, *renames, '-c', window[window.index('-c') + 1], '-o', str(binary / 'native_window.o')]
    profile = [str(gcc), *flags, '-c', str(source), '-o', str(binary / 'window_profile.o')]
    for name, command in [('native_window', window), ('window_profile', profile)]:
        r = subprocess.run(command, capture_output=True, text=True)
        (binary / (name + '.log')).write_text(json.dumps(command) + '\n' + r.stdout + r.stderr)
        assert r.returncode == 0, r.stderr
    objects = [binary / 'native_window.o' if Path(p).name == 'native_window.o' else ROOT / p
               for p in baseline['objects_sha256']]
    objects.append(binary / 'window_profile.o')
    link = [str(gcc), *map(str, objects), '-Wl,--stack,16777216', '-o', str(binary / 'dbaa_game.exe'),
            '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    r = subprocess.run(link, capture_output=True, text=True)
    (binary / 'link.log').write_text(json.dumps(link) + '\n' + r.stdout + r.stderr)
    assert r.returncode == 0, r.stderr
    proof = dict(baseline)
    proof.update(executable_sha256=sha(binary / 'dbaa_game.exe'), test_only_profile=True,
                 baseline_sha256=sha(stage / 'build.json'), builder_sha256=sha(__file__),
                 profile_source_sha256=sha(source), objects_sha256={label(p): sha(p) for p in objects},
                 link_command=link)
    (out / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    print('Built isolated window timing probe:', binary / 'dbaa_game.exe')


if __name__ == '__main__':
    main()
