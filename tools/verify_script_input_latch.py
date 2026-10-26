"""Verify numeric script event boundaries, repeat reads, same-frame overrides and EOF."""
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
    stage, out = args.game_stage.resolve(), args.out_dir.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    build = json.loads((stage/'build.json').read_text())
    for key in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT/p) == h for p, h in build[key].items()), key
    command = build['compile']['runtime']['command']
    gcc = Path(command[0])
    objects = []
    for name in build['objects_sha256']:
        p = ROOT/name
        if p.name == 'native_bridge.o':
            target = out/'bridge_probe.o'
            subprocess.run([str(gcc.with_name('objcopy.exe')), '--redefine-sym', 'main=Dbaa_UnusedGameMain', str(p), str(target)], check=True)
            p = target
        objects.append(p)
    source = ROOT/'tools/native_script_input_probe.c'
    command = [*command[:command.index('-c')], '-Wall', '-Wextra', '-Werror', str(source), *map(str, objects),
               '-Wl,--stack,16777216', '-o', str(out/'probe.exe'), '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    r = subprocess.run(command, capture_output=True, text=True)
    (out/'build.log').write_text(json.dumps(command)+'\n'+r.stdout+r.stderr)
    assert not r.returncode, r.stderr
    script = out/'input.txt'
    events = [(0,0), (1,1), (2,0), (3,3), (4,16), (4,48), (7,0), (9,128), (10,0)]
    script.write_text(''.join(f'{frame} {keys:x}\n' for frame,keys in events))
    sandbox = out/'sandbox'
    sandbox.mkdir(); shutil.copyfile(ROOT/'baserom.gba', sandbox/'probe.gba')
    env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0', DBAA_GAME_AUDIO_REPORT=str(out/'audio.json'))
    r = subprocess.run([str(out/'probe.exe'), str(sandbox/'probe.gba'), str(script)], cwd=sandbox,
                       env=env, capture_output=True, text=True, timeout=60)
    (out/'run.log').write_text(r.stdout+r.stderr)
    assert not r.returncode, r.stderr
    rows = [list(map(int, line.split())) for line in r.stdout.splitlines()]
    assert len(rows) == 12 and all(len(row)==3 for row in rows)
    expected = [1,0,3,48,48,48,0,0,128,0,0,0]
    different = [i+1 for i,row in enumerate(rows) if row != [i+1, expected[i], expected[i]]]
    report = dict(frames=12, reads=24, mismatches=len(different), different_frames=different,
                  actual=rows, expected=expected, event_at_frame_N_available_before_sample_N=not different,
                  repeat_reads_stable=all(row[1]==row[2] for row in rows),
                  guest_game_code_executed=False, windows_physical_keys_changed=False,
                  native_cpu_interpreter_linked=False, full_game_validated=False,
                  baseline_sha256=sha(stage/'build.json'), tool_sha256=sha(__file__), source_sha256=sha(source))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'source_snapshot.c').write_bytes(source.read_bytes())
    (out/'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    assert bool(different) == args.expect_failure, different
    print('PASS' if not different else 'EXPECTED OLD SCRIPT LATCH FAILURE', len(different), 'different frame samples')


if __name__ == '__main__':
    main()
