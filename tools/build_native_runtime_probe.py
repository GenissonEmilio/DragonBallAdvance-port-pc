"""Isolate a runtime mutation against an explicitly selected native game build."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    selected = parser.add_mutually_exclusive_group(required=True)
    selected.add_argument('--runtime-source', type=Path)
    selected.add_argument('--display-source', type=Path)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--game-layout', action='store_true', help='write bin/sandbox directories for scenario tools')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    binary = out / 'bin' if args.game_layout else out
    binary.mkdir(exist_ok=True)
    executable = binary / 'dbaa_game.exe'
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    label = lambda p: str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)
    baseline = json.loads(args.baseline.read_text())
    unit = 'runtime' if args.runtime_source else 'display'
    original = ROOT / 'tools/local/sp00nz_gbarecomp/src' / (unit + '.c')
    for field in ['sources_sha256', 'headers_sha256']:
        for path, digest in baseline[field].items():
            if ROOT / path != original:
                assert sha(ROOT / path) == digest, path
    source = (args.runtime_source or args.display_source).resolve()
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    assert baseline['compiler_sha256'] == sha(gcc)
    command = list(baseline['compile'][unit]['command'])
    command[command.index('-c') + 1] = str(source)
    command[command.index('-o') + 1] = str(out / (unit + '.o'))
    result = subprocess.run(command, capture_output=True, text=True)
    (out / (unit + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    objects = []
    for path, digest in baseline['objects_sha256'].items():
        p = ROOT / path
        if p.name == unit + '.o':
            p = out / (unit + '.o')
        else:
            assert sha(p) == digest, p
        objects.append(p)
    link = [str(gcc), *map(str, objects), '-Wl,--stack,16777216', '-o', str(executable),
            '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    result = subprocess.run(link, capture_output=True, text=True)
    (out / 'link.log').write_text(json.dumps(link) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    proof = dict(baseline)
    proof['sources_sha256'] = dict(baseline['sources_sha256'])
    proof['sources_sha256'].pop(label(original))
    proof['sources_sha256'][label(source)] = sha(source)
    proof['compile'] = dict(baseline['compile'])
    proof['compile'][unit] = dict(command=command, returncode=0, cached=False)
    proof.update(objects_sha256={label(p): sha(p) for p in objects},
                 executable_sha256=sha(executable), clean_source_build=False, historical_objects_reused=True,
                 runtime_probe=unit == 'runtime', display_probe=unit == 'display',
                 tool_sha256=sha(__file__), baseline_sha256=sha(args.baseline))
    (out / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    if args.game_layout:
        import shutil
        sandbox = out / 'sandbox'
        sandbox.mkdir(exist_ok=True)
        target = sandbox / 'baserom.gba'
        if target.exists():
            assert sha(target) == sha(ROOT / 'baserom.gba')
        else:
            shutil.copyfile(ROOT / 'baserom.gba', target)
    print('Built isolated native', unit, 'probe')


if __name__ == '__main__':
    main()
