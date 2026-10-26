"""Build and exercise this process's hidden asynchronous Win32 window."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_async_window_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve previous test evidence'
    out.mkdir(parents=True)
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    sources = [ROOT / p for p in ['tools/game_window_async_probe.c', 'port/windows/game_window_async.c',
                                  'port/native/audio_runtime.c', 'port/audio/audio_helpers.c',
                                  'port/audio/music_player_update.c']]
    headers = [p for folder in ['port/include', 'port/native', 'port/windows']
               for p in (ROOT / folder).glob('*.h')]
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in [*sources, *headers]}
    command = [str(gcc), '-std=c11', '-O2', '-ffunction-sections', '-fdata-sections', '-DDBAA_WINDOW_TEST',
               *['-I' + str(ROOT / p) for p in ['port/windows', 'port/native', 'port/include']],
               *map(str, sources), '-Wl,--gc-sections', '-o', str(out / 'probe.exe'), '-lgdi32', '-luser32', '-lm']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'compile.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([str(out / 'probe.exe')], capture_output=True, text=True, timeout=15)
    (out / 'probe.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report['ok'] and report['keys_tested'] == 10 and report['close_and_reopen']
    assert report['publisher_independent_of_stalled_ui'] and report['published_while_ui_blocked'] == 100
    assert all(sha(ROOT / p) == h for p, h in hashes.items())
    report.update(tool_sha256=sha(__file__), inputs_sha256=hashes, compiler_sha256=sha(gcc),
                  executable_sha256=sha(out / 'probe.exe'), compile_command=command,
                  own_process_window_only=True, synthetic_stall_not_actual_gpu_stall=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS asynchronous Win32 window: input, focus, close/reopen, pacing and independence from stalled UI')


if __name__ == '__main__':
    main()
