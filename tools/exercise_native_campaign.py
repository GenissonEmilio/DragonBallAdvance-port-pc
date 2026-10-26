"""Exercise ordinary gameplay buttons; never alter game RAM, ROM or health."""
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
    parser.add_argument('--game-stage', type=Path, default=ROOT / 'build/windows_native')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=60000)
    parser.add_argument('--save', type=Path)
    parser.add_argument('--jump-hold', type=int, default=12)
    parser.add_argument('--attack-delay', type=int, default=0)
    parser.add_argument('--walk', type=int, default=100)
    parser.add_argument('--period', type=int, default=240)
    parser.add_argument('--dump-at', type=int, action='append', default=[])
    args = parser.parse_args()
    assert args.frames > 2700 and 1 <= args.jump_hold <= 60
    assert 0 <= args.attack_delay <= 60
    assert args.period >= 120 and 0 < args.walk < args.period - 8
    stage, out = args.game_stage.resolve(), args.out_dir.resolve()
    assert not out.exists(), 'preserve earlier exercise; choose a new output directory'
    out.mkdir(parents=True)
    sandbox = out / 'sandbox'
    sandbox.mkdir()
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    exe = stage / 'bin/dbaa_game.exe'
    proof = json.loads((stage / 'build.json').read_text())
    assert sha(exe) == proof['executable_sha256'] and not proof['native_cpu_core_linked']
    shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
    if args.save:
        assert args.save.stat().st_size == 512
        shutil.copyfile(args.save, sandbox / 'baserom.eep')
    events = [(1300, 8), (1302, 0), (1420, 1), (1422, 0), (1540, 1), (1542, 0),
              (1660, 8), (1662, 0), (1780, 1), (1782, 0), (1900, 1), (1902, 0),
              (2400, 8), (2402, 0), (2500, 1), (2502, 0), (2580, 1), (2582, 0),
              (2660, 1), (2662, 0)]
    previous = None
    for frame in range(2700, args.frames + 1):
        offset = (frame - 2700) % args.period
        direction = 16 if offset < args.walk or args.period - 40 <= offset < args.period - 36 else (32 if offset < args.walk + 4 else 0)
        key = direction | (2 if offset % 10 < 5 else 0)
        if offset % (args.period // 2) < args.attack_delay:
            key &= ~2
        if offset % (args.period // 2) < args.jump_hold:
            key |= 1
        if key != previous:
            events.append((frame, key))
            previous = key
    script = out / 'input.txt'
    script.write_text(''.join(f'{frame} {key:x}\n' for frame, key in events))
    command = [str(exe), str(sandbox / 'baserom.gba'), '--headless', '--frames', str(args.frames),
               '--input', str(script), '--screenshot', str(out / 'final.bmp'), '--log-every', '3000']
    for frame in sorted(set(args.dump_at)):
        assert 0 < frame <= args.frames
        command += ['--dump-at', str(frame), str(out / f'frame_{frame}.memory')]
    env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0', DBAA_NATIVE_REPORT=str(out / 'native.json'),
               DBAA_GAME_AUDIO_REPORT=str(out / 'audio.json'))
    before = {p.name: sha(p) for p in sandbox.glob('*.eep')}
    start = time.monotonic()
    result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True,
                            timeout=max(120, args.frames / 200))
    (out / 'log.txt').write_text(result.stdout + result.stderr)
    native = json.loads((out / 'native.json').read_text()) if (out / 'native.json').exists() else None
    report = dict(command=command, returncode=result.returncode, seconds=time.monotonic() - start,
                  executable_sha256=sha(exe), build_sha256=sha(stage / 'build.json'),
                  input_sha256=sha(script), tool_sha256=sha(__file__), native=native,
                  saves_before=before, saves_after={p.name: sha(p) for p in sandbox.glob('*.eep')},
                  ordinary_buttons_only=True, campaign_completed=False, whole_game_validated=False)
    (out / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    assert result.returncode == 0, result.stderr[-2000:]
    assert native['frames'] == args.frames and native['fallback_failures'] == 0
    print('Completed ordinary-input exercise:', args.frames, 'frames;', out)


if __name__ == '__main__':
    main()
