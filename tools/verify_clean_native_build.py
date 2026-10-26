"""Compare a fresh source build to the previously audited native game.

This is a build regression check. It does not establish whole-game ROM parity.
Both executables run the same ordinary input from identical erased saves.
"""
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
    parser.add_argument('--baseline', type=Path, default=ROOT / 'build/next/game_timing')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_clean_build_validation')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=20000)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'choose a fresh output directory to preserve earlier evidence'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    stages = dict(baseline=args.baseline.resolve(), clean=args.game_stage.resolve())
    reports = {}
    for name, stage in stages.items():
        build = json.loads((stage / 'build.json').read_text())
        exe = stage / 'bin/dbaa_game.exe'
        assert sha(exe) == build['executable_sha256'] and not build['native_cpu_core_linked']
        if name == 'clean':
            assert build['clean_source_build'] and not build['historical_objects_reused']
            assert all(not (ROOT / p).is_relative_to(ROOT / 'build/next') for p in build['objects_sha256'])
            assert all(not r['cached'] for r in build['compile'].values()), 'this check requires the first fresh build manifest'
        sandbox = out / name
        sandbox.mkdir()
        shutil.copyfile(ROOT / 'baserom.gba', sandbox / 'baserom.gba')
        command = [str(exe), str(sandbox / 'baserom.gba'), '--headless', '--frames', str(args.frames),
                   '--input', str(args.input.resolve()), '--screenshot', str(sandbox / 'final.bmp'),
                   '--dump-at', str(args.frames), str(sandbox / 'final.memory'), '--log-every', '1000']
        env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0',
                   DBAA_NATIVE_REPORT=str(sandbox / 'native.json'),
                   DBAA_GAME_AUDIO_REPORT=str(sandbox / 'audio.json'), DBAA_GAME_PCM=str(sandbox / 'game.pcm'))
        start = time.monotonic()
        result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True, timeout=180)
        (sandbox / 'log.txt').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr[-2000:]
        native, audio = [json.loads((sandbox / (n + '.json')).read_text()) for n in ['native', 'audio']]
        assert native['frames'] == args.frames and native['rom_validated'] and not native['fallback_failures']
        assert audio['ok'] and not audio['device_enabled'] and audio['device_error'] == 0
        reports[name] = dict(command=command, returncode=result.returncode, seconds=time.monotonic() - start,
                             executable_sha256=sha(exe), build_sha256=sha(stage / 'build.json'),
                             native=native, audio=audio,
                             output_sha256={p.name: sha(p) for p in sandbox.iterdir()
                                            if p.name in ['final.bmp', 'final.memory', 'game.pcm'] or p.suffix in ['.eep', '.sav']})
        print('Executed', name, args.frames, 'frames', flush=True)
    a, b = reports.values()
    assert a['native'] == b['native'], 'native execution diagnostics differ'
    assert a['audio'] == b['audio'], 'audio diagnostics differ'
    assert a['output_sha256'] == b['output_sha256'], 'PCM, memory, image or save bytes differ'
    report = dict(frames=args.frames, reports=reports, tool_sha256=sha(__file__),
                  input_sha256=sha(args.input), clean_build_equal_to_audited_native=True,
                  memory_bytes_equal=True, image_bytes_equal=True, pcm_bytes_equal=True, save_bytes_equal=True,
                  historical_objects_reused=False, whole_game_rom_parity=False, port_complete=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS clean source build: full memory, image, PCM, save and diagnostics equal audited native build')


if __name__ == '__main__':
    main()
