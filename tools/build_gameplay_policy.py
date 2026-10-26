"""Attach an observational, ordinary-button test controller to a native build."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=ROOT / 'build/windows_native')
    parser.add_argument('--source', type=Path, default=ROOT / 'tools/gameplay_policy.c')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_gameplay_policy')
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
    display = list(baseline['compile']['display']['command'])
    gcc = display[0]
    flags = display[1:display.index('-c')]
    original = display[display.index('-c') + 1]
    display = [gcc, *flags, '-Ddisplay_get_keys=dbaa_policy_original_keys', '-c', original, '-o', str(binary / 'display.o')]
    source = args.source.resolve()
    (out / 'policy_source.c').write_bytes(source.read_bytes())
    (out / 'builder_source.py').write_bytes(Path(__file__).read_bytes())
    local_headers = [source.parent / n for n in re.findall(r'^#include "([^"]+)"', source.read_text(), re.M)
                     if (source.parent / n).is_file()]
    policy_headers = {label(p): sha(p) for p in local_headers}
    for p in local_headers:
        (out / p.name).write_bytes(p.read_bytes())
    policy = [gcc, *flags, '-Wall', '-Wextra', '-Werror', '-c', str(source), '-o', str(binary / 'policy.o')]
    audio = list(baseline['compile']['game_audio']['command'])
    audio.insert(audio.index('-c'), '-DDbaa_GameAudioBindMemory=dbaa_policy_original_bind')
    audio[audio.index('-o') + 1] = str(binary / 'game_audio.o')
    for name, command in [('display', display), ('policy', policy), ('game_audio', audio)]:
        result = subprocess.run(command, capture_output=True, text=True)
        (binary / (name + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
    objects = [binary / Path(p).name if Path(p).name in ['display.o', 'game_audio.o'] else ROOT / p
               for p in baseline['objects_sha256']]
    objects.append(binary / 'policy.o')
    link = [gcc, *map(str, objects), '-Wl,--stack,16777216', '-o', str(binary / 'dbaa_game.exe'),
            '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    result = subprocess.run(link, capture_output=True, text=True)
    (binary / 'link.log').write_text(json.dumps(link) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    proof = dict(baseline)
    proof.update(executable_sha256=sha(binary / 'dbaa_game.exe'), observational_policy=True,
                 policy_headers_sha256=policy_headers,
                 policy_guest_memory_writes=False, source_sha256=sha(source), builder_sha256=sha(__file__),
                 baseline_sha256=sha(stage / 'build.json'), objects_sha256={label(p): sha(p) for p in objects},
                 link_command=link)
    assert all(sha(ROOT / p) == h for p, h in policy_headers.items()), 'policy header changed during build'
    (out / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    print('Built observation-driven button controller:', binary / 'dbaa_game.exe')


if __name__ == '__main__':
    main()
