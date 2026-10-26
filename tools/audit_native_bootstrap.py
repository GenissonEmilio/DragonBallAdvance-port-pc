"""Preserve the independent installation/build and observational replay proofs."""
from pathlib import Path
import hashlib
import json

ROOT = Path.cwd()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def main():
    previous_path = ROOT / 'build/next/clean_game/verification.json'
    previous = read(previous_path)
    assert previous['production_functions'] == 265 and previous['production_bytes'] == 36576
    assert previous['cgb_driver_songs'] == 9 and not previous['port_complete']
    assert previous['canonical_build_sha256'] == sha(ROOT / 'build/windows_native/build.json')
    frozen = read(ROOT / 'build/next/song_playback/frozen_inputs.json')
    assert all(sha(ROOT / p) == h for p, h in frozen.items())
    directory = ROOT / 'build/native_isolated_build_validation'
    proof = read(directory / 'report.json')
    assert proof['tool_sha256'] == sha(ROOT / 'tools/verify_isolated_native_build.py')
    assert proof['setup_and_public_build_passed'] and proof['native_objects_freshly_compiled'] == 108
    assert proof['no_extracted_toolchain_or_objects_inherited'] and proof['root_native_pipeline_sources_same']
    assert proof['full_guest_memory_image_pcm_save_equal'] and proof['frames'] == 20000
    assert proof['setup_sha256'] == sha(ROOT / 'tools/setup_native.ps1')
    assert proof['regression_sha256'] == sha(directory / 'regression/report.json')
    install = ROOT / 'build/native_cleanroom_second'
    project = install / 'project'
    assert proof['staged_sources_sha256'] == sha(install / 'staged_sources.json')
    assert proof['native_build_sha256'] == sha(project / 'build/windows_native/build.json')
    build = read(project / 'build/windows_native/build.json')
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(project / p) == h for p, h in build[field].items())
    regression = read(directory / 'regression/report.json')
    for name, run in regression['reports'].items():
        for p, h in run['output_sha256'].items():
            assert sha(directory / 'regression' / name / p) == h
    replay_path = ROOT / 'build/native_campaign_observed_v2_replay/report.json'
    replay = read(replay_path)
    assert replay['frames'] == 60000 and replay['ordinary_buttons_replayed_in_uninstrumented_game']
    assert replay['guest_memory_bytes_equal'] and replay['image_bytes_equal'] and replay['save_bytes_equal']
    assert replay['audio_diagnostics_and_fnv_equal'] and not replay['raw_pcm_bytes_compared']
    assert replay['tool_sha256'] == sha(ROOT / 'tools/replay_gameplay_policy.py')
    assert replay['baseline_build_sha256'] == sha(ROOT / 'build/windows_native/build.json')
    out = ROOT / 'build/next/native_bootstrap'
    out.mkdir(exist_ok=True)
    report = dict(previous)
    report.update(stage='independent_windows_bootstrap_and_observational_replay',
                  bootstrap_with_fresh_dependencies_tested=True,
                  independent_source_files=527, independent_fresh_objects=108,
                  independent_regression_frames=20000, independent_guest_memory_image_pcm_save_equal=True,
                  setup_gui_extractor_wait_fixed=True, setup_sha256=proof['setup_sha256'],
                  bootstrap_report_sha256=sha(directory / 'report.json'),
                  controller_replay_frames=60000, controller_replay_memory_image_save_equal=True,
                  controller_replay_audio_fnv_equal=True, controller_replay_raw_pcm_compared=False,
                  controller_replay_sha256=sha(replay_path), previous_milestone_sha256=sha(previous_path),
                  tool_sha256=sha(__file__), campaign_progress_save_validated=False,
                  whole_game_validated=False, port_complete=False, code_published=False)
    (out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'build/verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('AUDIT OK: independent Windows setup/source build and20k equivalence; observational60000-frame input replay preserved.')
    print('Campaign progress save, remaining game paths and final publication are pending.')


if __name__ == '__main__':
    main()
