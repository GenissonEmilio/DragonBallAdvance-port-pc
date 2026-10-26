"""Audit the ISA fix, original matching targets and separate clean native build."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    stage = ROOT / 'build/next/shift_flags'
    good_dir = ROOT / 'build/native_static_shift_validation_v5'
    good = json.loads((good_dir / 'report.json').read_text())
    # The only later validator edit added a reduced negative-baseline option
    # and source snapshots. Recover and hash the exact version used for v5.
    lines = (ROOT / 'tools/verify_static_shifts.py').read_text().splitlines(keepends=True)
    added = ["parser.add_argument('--thumb-only'", 'if args.thumb_only:',
             "samples = [s for s in samples if s['mode'] == 'T']",
             "(out / 'tool_snapshot.py').write_bytes", "(out / 'emitter_snapshot.c').write_bytes",
             'thumb_only=args.thumb_only,']
    snapshot = ''.join(line for line in lines if not any(s in line for s in added)).encode()
    assert hashlib.sha256(snapshot).hexdigest() == good['tool_sha256']
    snap_path = good_dir / 'tool_snapshot.py'
    if snap_path.exists():
        assert snap_path.read_bytes() == snapshot
    else:
        snap_path.write_bytes(snapshot)
    emitter = ROOT / 'tools/native_shift_emit.c'
    assert sha(emitter) == good['emitter_sha256']
    (good_dir / 'emitter_snapshot.c').write_bytes(emitter.read_bytes())
    assert good['cases'] == 405376 and good['samples'] == 602
    assert good['nzcv_and_registers_equal'] and good['mismatches'] == 0
    assert not good['full_isa_validated'] and not good['cpu_cycles_compared']
    assert sha(good_dir / 'probe.c') == good['probe_source_sha256']
    for p, digest in good['translator_sources_sha256'].items():
        assert sha(p) == digest
    assert sha(ROOT / 'tools/local/sp00nz_gbarecomp/include/gba/gba_runtime.h') == good['runtime_header_sha256']
    old_dir = ROOT / 'build/native_static_shift_old_validation'
    old = json.loads((old_dir / 'report.json').read_text())
    assert old['cases'] == 40960 and old['mismatches'] == 18304 and old['thumb_only']
    assert not old['nzcv_and_registers_equal']
    assert sha(old_dir / 'tool_snapshot.py') == old['tool_sha256']
    for p, digest in old['translator_sources_sha256'].items():
        assert sha(p) == digest
    patch = ROOT / 'tools/patches/gbarecomp-native.patch'
    subprocess.run(['git', '-C', str(ROOT / 'tools/local/sp00nz_gbarecomp'),
                    'apply', '--reverse', '--check', str(patch)], check=True)
    # Recheck the entire old ELF .text sections, exact ROM bytes and all
    # 25 immutable native/audio corpora, without claiming a fresh test run.
    legacy = ROOT / 'build/next/song_playback/audit.py'
    exec(compile(legacy.read_text().split('suite=unittest.defaultTestLoader.discover', 1)[0], str(legacy), 'exec'), {})
    game = ROOT / 'build/windows_native_shift'
    build = json.loads((game / 'build.json').read_text())
    assert len(build['compile']) == 108 and all(not c['cached'] for c in build['compile'].values())
    assert build['clean_source_build'] and not build['historical_objects_reused'] and not build['native_cpu_core_linked']
    for key in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == digest for p, digest in build[key].items())
    assert sha(game / 'bin/dbaa_game.exe') == build['executable_sha256']
    regression_dir = ROOT / 'build/native_shift_build_regression'
    regression = json.loads((regression_dir / 'report.json').read_text())
    assert regression['frames'] == 20000 and not regression['whole_game_rom_parity']
    assert all(regression[k] for k in ['memory_bytes_equal', 'image_bytes_equal', 'pcm_bytes_equal', 'save_bytes_equal'])
    assert regression['reports']['clean']['build_sha256'] == sha(game / 'build.json')
    report = dict(instruction_cases=good['cases'], instruction_mismatches=0,
                  negative_old_thumb_cases=old['cases'], negative_old_thumb_mismatches=old['mismatches'],
                  production_functions=265, production_bytes=36576, old_native_corpora_rechecked=25,
                  clean_source_objects=108, native_cpu_interpreter_compiled=False,
                  regression_frames=20000, native_regression_memory_image_pcm_save_equal=True,
                  original_rom_whole_game_parity=False, port_complete=False,
                  executable_sha256=build['executable_sha256'], patch_sha256=sha(patch), tool_sha256=sha(__file__),
                  references_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                     [good_dir / 'report.json', old_dir / 'report.json', game / 'build.json', regression_dir / 'report.json']})
    (stage / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS ISA fix, preserved matching/audio proofs and fresh native build regression')


if __name__ == '__main__':
    main()
