"""Exercise the real PowerShell diagnostic allocator without a ROM or game."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    source = ROOT / 'port/windows/preview/Sessoes.ps1'
    harness = out / 'probe.ps1'
    harness.write_text('''param([string]$Source, [string]$Root, [string]$Stamp)
$ErrorActionPreference = 'Stop'
try {
    . $Source
    New-DbaaDiagnosticSession -Root $Root -Stamp $Stamp
} catch { Write-Output $_.Exception.Message; exit 4 }
''', encoding='utf-8')
    results = []

    def run(root, stamp='20261026-100000', failure=False):
        command = ['powershell.exe', '-NoProfile', '-File', str(harness),
                   '-Source', str(source), '-Root', str(root), '-Stamp', stamp]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode == (4 if failure else 0), result.stdout + result.stderr
        path = None if failure else Path(result.stdout.strip().splitlines()[-1])
        assert failure or path.is_dir()
        return dict(root=root.name, stamp=stamp, failed=failure, session=path.name if path else None)

    normal = out / 'normal'
    for stamp in ['20261026-100000', '20261026-100000', '20260101-000000']:
        results.append(run(normal, stamp))
    assert [x['session'].split('-')[0] for x in results] == ['000', '001', '002']
    sentinel = normal / results[0]['session'] / 'preserve.txt'
    sentinel.write_text('previous diagnostics')
    (normal / 'dump-sequence.txt').write_text('corrupt counter')
    results.append(run(normal))
    assert results[-1]['session'].startswith('003-')
    assert sentinel.read_text() == 'previous diagnostics'
    (normal / '999-dump-20260101-000000').mkdir()
    (normal / 'dump-sequence.txt').write_text('1\n')
    results.append(run(normal))
    assert results[-1]['session'].startswith('1000-')

    empty = out / 'empty'
    empty.mkdir()
    (empty / 'dump-sequence.txt').write_text('999\n')
    results.append(run(empty))
    assert results[-1]['session'].startswith('000-')

    parallel = out / 'parallel'
    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(pool.map(lambda _: run(parallel), range(4)))
    assert {x['session'].split('-')[0] for x in concurrent} == {'000', '001', '002', '003'}
    assert (parallel / 'dump-sequence.txt').read_text().strip() == '4'
    results += concurrent

    exhausted = out / 'exhausted'
    exhausted.mkdir()
    (exhausted / '4294967295-dump-20261026-100000').mkdir()
    results.append(run(exhausted, failure=True))
    invalid = out / 'invalid'
    results.append(run(invalid, '../invalid', failure=True))
    assert not invalid.exists()
    report = dict(processes=len(results), concurrent_processes=4, checks_passed=True,
                  repeated_clock_preserves_sessions=True, backwards_clock_preserves_order=True,
                  corrupt_counter_recovered=True, stale_counter_recovered=True,
                  empty_directory_resets_sequence=True, exhausted_sequence_rejected=True,
                  invalid_timestamp_rejected=True, previous_capture_unchanged=True,
                  rom_required=False, game_executed=False,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), results=results)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS numbered diagnostic sessions:', len(results), 'processes including four concurrent launchers')


if __name__ == '__main__':
    main()
