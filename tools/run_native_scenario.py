"""Run existing ordinary inputs with an isolated save; capture native evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-stage', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--save', type=Path)
    parser.add_argument('--frames', type=int, default=6000)
    parser.add_argument('--pcm', action='store_true')
    args = parser.parse_args()
    out, stage = args.out_dir.resolve(), args.game_stage.resolve()
    required_space = 64 * 1024 * 1024 + (args.frames * 805 * 4 if args.pcm else 0)
    assert shutil.disk_usage(ROOT).free >= required_space, 'insufficient disk space for isolated ROM and test outputs'
    assert not out.exists(), 'preserve earlier evidence'
    out.mkdir(parents=True)
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    proof = json.loads((stage / 'build.json').read_text())
    exe = stage / 'bin/dbaa_game.exe'
    assert sha(exe) == proof['executable_sha256'] and not proof['native_cpu_core_linked']
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    if args.save:
        assert args.save.stat().st_size == 512
        shutil.copyfile(args.save, sandbox / 'baserom.eep')
    (out / 'input.txt').write_bytes(args.input.read_bytes())
    (out / 'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    before_saves = {p.name: sha(p) for p in sandbox.glob('*.eep')}
    command = [str(exe), str(sandbox / 'baserom.gba'), '--headless', '--frames', str(args.frames),
               '--input', str(out / 'input.txt'), '--screenshot', str(out / 'final.bmp'),
               '--dump-at', str(args.frames), str(out / 'final.memory'), '--log-every', '3000']
    env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0', DBAA_NATIVE_REPORT=str(out / 'native.json'),
               DBAA_GAME_AUDIO_REPORT=str(out / 'audio.json'))
    env.pop('DBAA_GAME_PCM', None)
    if args.pcm:
        env['DBAA_GAME_PCM'] = str(out / 'game.pcm')
    start = time.monotonic()
    result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True,
                            timeout=max(120, args.frames / 150))
    (out / 'log.txt').write_text(result.stdout + result.stderr)
    native = json.loads((out / 'native.json').read_text()) if (out / 'native.json').exists() else None
    report = dict(command=command, returncode=result.returncode, seconds=time.monotonic()-start,
                  executable_sha256=sha(exe), build_sha256=sha(stage / 'build.json'),
                  input_sha256=sha(out / 'input.txt'), tool_sha256=sha(__file__), native=native,
                  saves_before=before_saves, saves_after={p.name: sha(p) for p in sandbox.glob('*.eep')},
                  observational_policy=bool(proof.get('observational_policy')),
                  ordinary_buttons_only=True, campaign_completed=False, whole_game_validated=False,
                  output_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file()})
    (out / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    assert result.returncode == 0, result.stderr[-2000:]
    assert native['frames'] == args.frames and native['fallback_failures'] == 0
    print('Ran native scenario:', args.frames, 'frames;', out, flush=True)


if __name__ == '__main__':
    main()
