"""Verify an independently installed source tree and compare its game outputs."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installation', type=Path, default=ROOT / 'build/native_cleanroom_second')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_isolated_build_validation')
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    installation, out = args.installation.resolve(), args.out_dir.resolve()
    assert not out.exists(), 'use a fresh validation directory'
    out.mkdir(parents=True)
    project = installation / 'project'
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    read = lambda p: json.loads(Path(p).read_text())
    status = read(installation / 'terminal_results.json')
    assert status['setup_exit_code'] == status['public_build_exit_code'] == 0
    staged = read(installation / 'staged_sources.json')
    assert len(staged) == 527 and all(sha(project / p) == h for p, h in staged.items())
    stage = project / 'build/windows_native'
    build = read(stage / 'build.json')
    assert build['clean_source_build'] and not build['historical_objects_reused'] and not build['native_cpu_core_linked']
    assert len(build['compile']) == len(build['objects_sha256']) == 108
    assert all(not r['cached'] and r['returncode'] == 0 for r in build['compile'].values())
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        for path, digest in build[field].items():
            p = (project / path).resolve()
            assert p.is_relative_to(project) and sha(p) == digest, (field, path)
            assert not p.is_relative_to(project / 'build/next')
    for name, row in build['compile'].items():
        command = row['command']
        assert Path(command[0]).is_relative_to(project / 'tools/local/w64devkit')
        for option in ['-c', '-o']:
            assert Path(command[command.index(option) + 1]).is_relative_to(project), name
    assert build['builder_sha256'] == sha(project / 'tools/build_native_game.py')
    assert build['builder_sha256'] == sha(ROOT / 'tools/build_native_game.py')
    assert sha(stage / 'bin/dbaa_game.exe') == build['executable_sha256']
    assert 'Native dependencies ready.' in (installation / 'setup_console.log').read_text()
    assert sha(project / 'tools/setup_native.ps1') == sha(ROOT / 'tools/setup_native.ps1')
    generation = read(project / 'build/windows_native_generation/generation.json')
    assert generation['seed_entries'] == 264 and generation['combined_extra_candidates'] == 2364
    assert generation['compiler_sha256'] == build['compiler_sha256'] == sha(ROOT / 'tools/local/w64devkit/bin/gcc.exe')
    assert generation['rom_sha1'] == '1338584d8cfa57402603197e65d2e2ff0184d24f'
    for p, h in generation['generated_files_sha256'].items():
        assert sha(Path(generation['source_directory']) / p) == h
    line_endings = []
    for p, h in generation['source_inputs_sha256'].items():
        assert sha(project / p) == h
        a, b = (project / p).read_bytes(), (ROOT / p).read_bytes()
        if a != b:
            assert a.replace(b'\r\n', b'\n') == b.replace(b'\r\n', b'\n'), p
            line_endings.append(p)
    # Fresh checkouts use LF; older local files had CRLF. Do not normalize any
    # ROM/output bytes, and do not claim their exact source fingerprints match.
    command = [sys.executable, '-X', 'utf8', str(ROOT / 'tools/verify_clean_native_build.py'),
               '--baseline', str(ROOT / 'build/windows_native'), '--game-stage', str(stage),
               '--out-dir', str(out / 'regression'), '--input', str(args.input.resolve()), '--frames', '20000']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240)
    (out / 'regression.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    regression = read(out / 'regression/report.json')
    assert regression['clean_build_equal_to_audited_native'] and regression['memory_bytes_equal']
    report = dict(source_files_staged=527, native_objects_freshly_compiled=108,
                  no_extracted_toolchain_or_objects_inherited=True,
                  verified_compiler_download_archive_cached=True,
                  source_dependencies_fetched=True, python_environment_new=True,
                  setup_and_public_build_passed=True, native_cpu_interpreter_compiled=False,
                  root_native_pipeline_sources_same=True, upstream_line_endings_differ_only=line_endings,
                  frames=20000, full_guest_memory_image_pcm_save_equal=True,
                  setup_sha256=sha(project / 'tools/setup_native.ps1'),
                  staged_sources_sha256=sha(installation / 'staged_sources.json'),
                  native_build_sha256=sha(stage / 'build.json'),
                  generation_manifest_sha256=sha(project / 'build/windows_native_generation/generation.json'),
                  regression_sha256=sha(out / 'regression/report.json'), tool_sha256=sha(__file__),
                  whole_game_rom_parity=False, campaign_complete=False, port_complete=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS isolated bootstrap and public build:108 fresh objects,20k frames memory/image/PCM/save equal root native game')


if __name__ == '__main__':
    main()
