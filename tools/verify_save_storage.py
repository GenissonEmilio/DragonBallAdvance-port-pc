"""Validate complete replacement, failure preservation and killed child writes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import stat
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_save_storage_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    source = ROOT / 'port/windows/save_storage.c'
    probe = ROOT / 'tools/save_storage_probe.c'
    exe = out / 'storage_probe.exe'
    command = [str(gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
               '-I' + str(ROOT / 'port/windows'), str(source), str(probe), '-o', str(exe)]
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    payload = lambda size, k: bytes((i * 73 + k) & 255 for i in range(size))
    results = []
    for size in [512, 8192]:
        folder = out / str(size)
        folder.mkdir(exist_ok=True)
        target = folder / 'save.eep'
        old = b'\x37' * size
        target.write_bytes(old)
        result = subprocess.run([str(exe), str(target), str(size), '2'], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert target.read_bytes() == payload(size, 0x5A)
        target.write_bytes(old)
        target.chmod(stat.S_IREAD)
        try:
            result = subprocess.run([str(exe), str(target), str(size), '1'], capture_output=True, text=True)
            assert result.returncode == 1, result.stdout + result.stderr
            assert json.loads(result.stdout)['error'] != 0
            assert target.read_bytes() == old
        finally:
            target.chmod(stat.S_IREAD | stat.S_IWRITE)
        assert not list(folder.glob('*.tmp.*')), 'failed write left a temporary file'
        result = subprocess.run([str(exe), str(target), '0', '1'], capture_output=True, text=True)
        assert result.returncode == 1 and json.loads(result.stdout)['error'] == 87
        assert target.read_bytes() == old
        kills = []
        for case in range(6):
            target.write_bytes(old)
            process = subprocess.Popen([str(exe), str(target), str(size), '100000'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            staged = False
            deadline = time.monotonic() + 5
            try:
                while process.poll() is None and time.monotonic() < deadline:
                    if list(folder.glob(f'save.eep.tmp.{process.pid}.*')):
                        staged = True
                        break
                    time.sleep(0.001)
                assert staged and process.poll() is None, 'writer was not observed live with a staged sibling'
                process.kill()  # Only this verifier's newly created child.
                process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
            actual = target.read_bytes()
            assert actual in [old, payload(size, 0xA5), payload(size, 0x5A)], 'torn save after child termination'
            kills.append(dict(staged_sibling_observed=True, child_returncode=process.returncode,
                              target_sha256=sha(target), target_bytes=len(actual)))
            # A hard kill can leave its unique sibling; it must not be loaded
            # as the actual save. Remove only this child's own test siblings.
            for temporary in folder.glob(f'save.eep.tmp.{process.pid}.*'):
                temporary.unlink()
            result = subprocess.run([str(exe), str(target), str(size), '1'], capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            assert target.read_bytes() == payload(size, 0xA5)
        results.append(dict(bytes=size, replace_equal=True, read_only_failure_preserved=True,
                            empty_payload_rejected=True, process_kill_cases=kills))
    report = dict(sizes=[512, 8192], process_kill_cases=12, all_targets_complete=True,
                  writes_recover_after_kill=True, read_only_failure_preserves_original=True,
                  actual_power_loss_tested=False, network_filesystem_tested=False,
                  results=results, source_sha256=sha(source), header_sha256=sha(ROOT / 'port/windows/save_storage.h'),
                  probe_sha256=sha(probe), tool_sha256=sha(__file__), executable_sha256=sha(exe))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS save storage: 512/8192 bytes, read-only/empty rejection, 12 live child terminations; all target files complete')


if __name__ == '__main__':
    main()
