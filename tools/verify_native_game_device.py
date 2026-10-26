"""Compare offline native-game PCM and actual WASAPI submission, same seed."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'build/next/game_audio'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_game_device_validation')
    parser.add_argument('--frames', type=int, default=1200)
    parser.add_argument('--window', action='store_true', help='exercise a hidden Win32 window with QPC pacing')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--game-stage', type=Path, default=STAGE)
    args = parser.parse_args(argv)
    required_space = 128 * 1024 * 1024 + args.frames * 805 * 8
    assert shutil.disk_usage(ROOT).free >= required_space, 'insufficient disk space for two isolated ROM/PCM runs'
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    (out / 'failed_quality_report.json').unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    stage = args.game_stage.resolve()
    exe = stage / 'bin/dbaa_game.exe'
    proof = json.loads((stage / 'build.json').read_text())
    assert proof['executable_sha256'] == sha(exe)
    assert proof['game_audio_connected'] and not proof['native_cpu_core_linked']
    reports = {}
    initial = {}
    for name, device in [('offline', 0), ('wasapi', 1)]:
        sandbox = out / ('sandbox_' + name)
        sandbox.mkdir(exist_ok=True)
        for filename in ['baserom.gba', 'baserom.eep', 'baserom.sav']:
            source = stage / 'sandbox' / filename
            if source.exists():
                shutil.copyfile(source, sandbox / filename)
        seed = {p.name: sha(p) for p in sandbox.iterdir() if p.suffix in ['.gba', '.eep', '.sav']}
        if not initial:
            initial = seed
        assert initial == seed, 'offline/device starting files differ'
        command = [str(exe), str(sandbox / 'baserom.gba'), '--frames', str(args.frames),
                   '--screenshot', str(out / (name + '.bmp')), '--log-every', '300']
        # Offline rendering is unpaced. The device variant optionally uses
        # the real Win32 presentation/pacing path without taking user focus.
        if not args.window or not device:
            command.append('--headless')
        if args.input:
            command += ['--input', str(args.input.resolve())]
        env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE=str(device),
                   DBAA_NATIVE_REPORT=str(out / (name + '.native.json')),
                   DBAA_GAME_AUDIO_REPORT=str(out / (name + '.audio.json')),
                   DBAA_GAME_PCM=str(out / (name + '.pcm')))
        startup = None
        if args.window and device:
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        before = time.monotonic()
        result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True,
                                text=True, startupinfo=startup,
                                timeout=max(90, args.frames / 59.7275 + 20))
        (out / (name + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        assert result.returncode == 0, (name, result.returncode, result.stderr[-1200:])
        native = json.loads((out / (name + '.native.json')).read_text())
        audio = json.loads((out / (name + '.audio.json')).read_text())
        assert native['frames'] == args.frames and native['rom_validated']
        assert native['fallback_failures'] == 0 and not native['cpu_interpreter_compiled']
        assert audio['ok'] and audio['device_enabled'] == bool(device)
        assert audio['stereo_samples'] > 0 and audio['pcm_source_nonzero_samples'] > 0
        assert audio['clipped'] == 0 and audio['device_error'] == 0
        assert not audio['whole_game_pcm_rom_equal']
        pcm_path = out / (name + '.pcm')
        assert pcm_path.stat().st_size == audio['stereo_samples'] * 4
        if device:
            assert audio['device_submitted'] == audio['stereo_samples']
            assert audio['device_pcm_fnv1a64'] == audio['pcm_fnv1a64']
        reports[name] = dict(native=native, audio=audio, seconds=time.monotonic() - before,
                             pcm_sha256=sha(pcm_path), image_sha256=sha(out / (name + '.bmp')),
                             saves_after={p.name: sha(p) for p in sandbox.iterdir() if p.suffix in ['.eep', '.sav']})
        print('Passed native game', name, args.frames, 'frames;', audio['stereo_samples'], 'stereo samples', flush=True)
    assert reports['offline']['native'] == reports['wasapi']['native']
    assert reports['offline']['audio']['cycles'] == reports['wasapi']['audio']['cycles']
    assert reports['offline']['pcm_sha256'] == reports['wasapi']['pcm_sha256']
    assert reports['offline']['image_sha256'] == reports['wasapi']['image_sha256']
    assert reports['offline']['saves_after'] == reports['wasapi']['saves_after']
    reference_pcm = json.loads((ROOT / 'build/native_game_audio_validation/report.json').read_text())
    assert reference_pcm['frames'] == 1800 and not reference_pcm['quick']
    assert reference_pcm['pcm16_equal_to_immutable_rom_corpus']
    assert all(sha(ROOT / p) == h for p, h in reference_pcm['native_build']['sources_sha256'].items())
    report = dict(frames=args.frames, window_backend=args.window, window_hidden=args.window, offline_headless=True,
                  native_cpu_interpreter_compiled=False, game_audio_connected=True,
                  wasapi_submission_equals_offline_game_pcm=True,
                  original_song_pcm_corpus_equal=reference_pcm['pcm16_equal_to_immutable_rom_corpus'],
                  original_song_stereo_samples=reference_pcm['stereo_samples'],
                  whole_game_pcm_rom_equal=False, whole_game_validated=False,
                  human_speaker_audibility_confirmed=False, analog_output_bit_exact=False,
                  initial_files=initial, reports=reports, executable_sha256=sha(exe),
                  build_report_sha256=sha(stage / 'build.json'), tool_sha256=sha(__file__),
                  continuous_playback_passed=reports['wasapi']['audio']['endpoint_empty'] == 0)
    if not report['continuous_playback_passed']:
        (out / 'failed_quality_report.json').write_text(json.dumps(report, indent=2) + '\n')
        print('FAIL continuous playback:', reports['wasapi']['audio']['endpoint_empty'],
              'endpoint empty events; full submitted PCM still equals offline PCM')
        return 1
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS native game WASAPI: submitted PCM exactly equals offline native game PCM')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
