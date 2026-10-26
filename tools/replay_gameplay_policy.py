"""Replay recorded policy buttons in the uninstrumented native game."""
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
    parser.add_argument('--observed', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--game-stage', type=Path, default=ROOT / 'build/windows_native')
    args = parser.parse_args()
    observed, out, stage = args.observed.resolve(), args.out_dir.resolve(), args.game_stage.resolve()
    assert not out.exists(), 'preserve earlier replay evidence'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    original = json.loads((observed / 'run.json').read_text())
    frames = original['native']['frames']
    assert original['returncode'] == 0 and original['ordinary_buttons_only']
    exe = stage / 'bin/dbaa_game.exe'
    build = json.loads((stage / 'build.json').read_text())
    assert sha(exe) == build['executable_sha256'] and not build['native_cpu_core_linked']
    shutil.copyfile(ROOT / 'baserom.gba', out / 'baserom.gba')
    for name, digest in original['saves_before'].items():
        seed = ROOT / 'build/native_game_save_boot_validation/boot_0.eep'
        assert sha(seed) == digest
        shutil.copyfile(seed, out / name)
    inputs = observed / 'sandbox/policy_input.txt'
    command = [str(exe), str(out / 'baserom.gba'), '--headless', '--frames', str(frames),
               '--input', str(inputs), '--screenshot', str(out / 'final.bmp'),
               '--dump-at', str(frames), str(out / 'final.memory'), '--log-every', '3000']
    env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0', DBAA_NATIVE_REPORT=str(out / 'native.json'),
               DBAA_GAME_AUDIO_REPORT=str(out / 'audio.json'))
    result = subprocess.run(command, cwd=out, env=env, capture_output=True, text=True,
                            timeout=max(120, frames / 200))
    (out / 'log.txt').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr[-1500:]
    native, audio = [json.loads((out / (n + '.json')).read_text()) for n in ['native', 'audio']]
    expected_audio = json.loads((observed / 'audio.json').read_text())
    assert native == original['native'], 'native diagnostics differ'
    assert audio == expected_audio, 'audio counters/hash differ'
    for candidate, reference in [('final.bmp', observed / 'final.bmp'),
                                  ('final.memory', observed / f'frame_{frames}.memory')]:
        assert (out / candidate).read_bytes() == reference.read_bytes(), candidate
    saves = {p.name: sha(p) for p in out.glob('*.eep')}
    assert saves == original['saves_after']
    report = dict(frames=frames, ordinary_buttons_replayed_in_uninstrumented_game=True,
                  guest_memory_bytes_equal=True, image_bytes_equal=True, save_bytes_equal=True,
                  audio_diagnostics_and_fnv_equal=True, raw_pcm_bytes_compared=False,
                  command=command, input_sha256=sha(inputs), observed_report_sha256=sha(observed / 'run.json'),
                  baseline_build_sha256=sha(stage / 'build.json'), tool_sha256=sha(__file__),
                  final_memory_sha256=sha(out / 'final.memory'), final_image_sha256=sha(out / 'final.bmp'),
                  whole_game_rom_parity=False, campaign_complete=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS observational policy replay:', frames, 'frames; full guest memory/image/save equal, audio diagnostics/FNV equal')


if __name__ == '__main__':
    main()
