"""Consolidate source-build, asynchronous window and original-driver evidence."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

ROOT = Path.cwd()
STAGE = ROOT / 'build/next/clean_game'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def sections(path):
    data = Path(path).read_bytes()
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    assert data[pe:pe + 4] == b'PE\0\0'
    machine, count = struct.unpack_from('<HH', data, pe + 4)
    optional = struct.unpack_from('<H', data, pe + 20)[0]
    assert machine == 0x8664 and struct.unpack_from('<H', data, pe + 24)[0] == 0x20B
    result = {}
    for index in range(count):
        at = pe + 24 + optional + index * 40
        name = data[at:at + 8].rstrip(b'\0').decode()
        virtual, address, size, offset = struct.unpack_from('<IIII', data, at + 8)
        result[name] = (virtual, address, size, data[offset:offset + size])
    return result


def main():
    legacy = ROOT / 'build/next/song_playback/audit.py'
    prefix = legacy.read_text().split('suite=unittest.defaultTestLoader.discover', 1)[0]
    exec(compile(prefix, str(legacy), 'exec'), {'__name__': 'matching_and_original_audio_audit'})
    archive = read(STAGE / 'first_build_archive.json')
    for path, record in archive.items():
        assert sha(ROOT / record['archive']) == record['sha256'], path

    def preserved(path, digest):
        p = ROOT / path
        if p.exists() and sha(p) == digest:
            return p
        record = archive.get(str(Path(path)))
        assert record and record['sha256'] == digest, path
        return ROOT / record['archive']

    first_path = ROOT / archive[str(Path('build/windows_native/build.json'))]['archive']
    first = read(first_path)
    assert first['clean_source_build'] and not first['historical_objects_reused']
    assert len(first['objects_sha256']) == 108 and all(not r['cached'] for r in first['compile'].values())
    assert first['builder_sha256'] == sha(ROOT / archive[str(Path('tools/build_native_game.py'))]['archive'])
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        for p, h in first[field].items():
            assert sha(preserved(p, h)) == h
    first_exe = preserved('build/windows_native/bin/dbaa_game.exe', first['executable_sha256'])
    assert not any((ROOT / p).is_relative_to(ROOT / 'build/next') for p in first['objects_sha256'])
    generation = read(ROOT / 'build/windows_native_generation/generation.json')
    assert generation['input_key'] == 'eab60c18b594593bd80de92de3a14d979dc0ba0ead28005348297210de2dbbc3'
    for p, h in generation['generated_files_sha256'].items():
        assert sha(Path(generation['source_directory']) / p) == h
    for p, h in generation['source_inputs_sha256'].items():
        assert sha(ROOT / p) == h
    timing = ROOT / 'build/next/game_timing'
    for p, h in read(timing / 'frozen_inputs.json').items():
        current = ROOT / p
        if sha(current) != h:
            current = timing / 'frozen_sources' / p
        assert sha(current) == h
    old_objects = {Path(p).name: h for p, h in read(timing / 'build.json')['objects_sha256'].items()}
    first_objects = {Path(p).name: h for p, h in first['objects_sha256'].items()}
    chip_names = [n + '.o' for n in ['psg', 'chip', 'timing', 'sync', 'audio_buffer', 'circle_buffer']]
    assert all(first_objects[n] == old_objects[n] for n in chip_names)
    regression_dir = ROOT / 'build/native_clean_build_validation'
    regression = read(regression_dir / 'report.json')
    assert regression['frames'] == 20000 and regression['clean_build_equal_to_audited_native']
    assert regression['tool_sha256'] == sha(ROOT / 'tools/verify_clean_native_build.py')
    assert regression['reports']['clean']['build_sha256'] == sha(first_path)
    assert regression['reports']['clean']['executable_sha256'] == sha(first_exe)
    a, b = regression['reports'].values()
    assert a['native'] == b['native'] and a['audio'] == b['audio']
    assert a['output_sha256'] == b['output_sha256']
    for name, run in regression['reports'].items():
        for p, h in run['output_sha256'].items():
            assert sha(regression_dir / name / p) == h
    assert (regression_dir / 'clean/final.memory').stat().st_size == 396288
    canonical_dir = ROOT / 'build/windows_native'
    variant_dir = ROOT / 'build/windows_native_async'
    canonical, variant = [read(p / 'build.json') for p in [canonical_dir, variant_dir]]
    for build in [canonical, variant]:
        assert not build['native_cpu_core_linked'] and build['game_audio_connected']
        for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
            assert all(sha(ROOT / p) == h for p, h in build[field].items()), field
    assert canonical['builder_sha256'] == sha(ROOT / 'tools/build_native_game.py')
    assert variant['builder_sha256'] == sha(ROOT / 'tools/build_native_window_variant.py')
    canonical_objects = {Path(p).name: h for p, h in canonical['objects_sha256'].items()}
    variant_objects = {Path(p).name: h for p, h in variant['objects_sha256'].items()}
    assert canonical_objects == variant_objects
    assert [n for n in canonical_objects if canonical_objects[n] != first_objects[n]] == ['native_window.o']
    exe, tested_exe = [p / 'bin/dbaa_game.exe' for p in [canonical_dir, variant_dir]]
    assert sha(exe) == canonical['executable_sha256'] and sha(tested_exe) == variant['executable_sha256']
    # A later PE link may change header timestamps/checksum. Compare every
    # named section's bytes, address and sizes; do not call this whole-file equality.
    assert sections(exe) == sections(tested_exe)
    symbols = subprocess.check_output([str(ROOT / 'tools/local/w64devkit/bin/nm.exe'), str(exe)], text=True)
    assert not any(x in symbols for x in ['run_iwram_function_', 'ARMRun', 'ARMStep', 'SM83Tick', 'GBACoreCreate'])
    sessions = {}
    for folder, frames, count, fnv in [('native_async_game_device_validation', 5000, 4018026, '044d06b01d1905e2'),
                                      ('native_async_game_long_validation', 20000, 16072761, '199d7f590635ad76')]:
        directory = ROOT / 'build' / folder
        proof = read(directory / 'report.json')
        assert proof['frames'] == frames and proof['continuous_playback_passed'] and proof['window_backend']
        assert proof['executable_sha256'] == sha(tested_exe) and proof['build_report_sha256'] == sha(variant_dir / 'build.json')
        assert proof['tool_sha256'] == sha(ROOT / 'tools/verify_native_game_device.py')
        off, on = [proof['reports'][n] for n in ['offline', 'wasapi']]
        assert off['native'] == on['native'] and off['native']['frames'] == frames
        assert off['image_sha256'] == on['image_sha256'] and off['pcm_sha256'] == on['pcm_sha256']
        assert off['saves_after'] == on['saves_after']
        for name, run in [('offline', off), ('wasapi', on)]:
            assert sha(directory / (name + '.pcm')) == run['pcm_sha256']
            assert sha(directory / (name + '.bmp')) == run['image_sha256']
        audio = on['audio']
        assert audio['device_submitted'] == audio['stereo_samples'] == count
        assert audio['device_pcm_fnv1a64'] == audio['pcm_fnv1a64'] == fnv
        assert audio['endpoint_empty'] == audio['device_error'] == audio['device_queue_remaining'] == 0
        assert audio['device_mmcss'] == 1 and '[window] Games MMCSS active; asynchronous GDI' in (directory / 'wasapi.log').read_text()
        sessions[str(frames)] = dict(samples=count, fnv1a64=fnv, report_sha256=sha(directory / 'report.json'))
    probe_dir = ROOT / 'build/native_async_window_validation'
    probe = read(probe_dir / 'report.json')
    assert probe['ok'] and probe['keys_tested'] == 10 and probe['close_and_reopen']
    assert probe['window_thread_distinct'] and probe['publisher_independent_of_stalled_ui']
    assert probe['published_while_ui_blocked'] == 100 and probe['paced_frames'] == 120
    assert probe['tool_sha256'] == sha(ROOT / 'tools/verify_async_window.py')
    assert all(sha(ROOT / p) == h for p, h in probe['inputs_sha256'].items())
    failed = {}
    for folder in ['native_clean_game_device_validation', 'native_window_profile_validation']:
        p = ROOT / 'build' / folder / 'failed_quality_report.json'
        proof = read(p)
        assert not proof['continuous_playback_passed'] and proof['wasapi_submission_equals_offline_game_pcm']
        assert proof['reports']['wasapi']['audio']['endpoint_empty'] > 0
        failed[folder] = dict(report_sha256=sha(p), empty_events=proof['reports']['wasapi']['audio']['endpoint_empty'])
    report = dict(updated='2026-10-23', stage='source_build_and_asynchronous_win32_presentation',
                  production_functions=265, production_bytes=36576, c_functions=242, c_bytes=33856,
                  assembly_functions=23, assembly_bytes=2720, gba_images_rechecked=True,
                  source_build_objects=108, historical_game_objects_reused=False,
                  native_cpu_interpreter_compiled=False, standalone_psg_objects_equal_prior_reference=True,
                  clean_build_regression_frames=20000, memory_bytes_equal=396288,
                  clean_build_image_pcm_save_equal=True, public_build_pipeline_executed=True,
                  public_exe=str(exe.relative_to(ROOT)), executable_sha256=sha(exe),
                  canonical_objects_equal_device_tested=True, canonical_pe_sections_equal_device_tested=True,
                  canonical_whole_file_equal_device_tested=exe.read_bytes() == tested_exe.read_bytes(),
                  asynchronous_window=True, window_keys_tested=10, window_stall_independence=True,
                  sessions=sessions, historical_sync_failures_preserved=failed,
                  last_full_suite_tests=514, tests_discovered=541, full_test_suite_reexecuted=False,
                  whole_game_pcm_rom_equal=False, campaign_progress_save_validated=False,
                  bootstrap_with_fresh_dependencies_tested=False, whole_game_validated=False, port_complete=False,
                  publication_authorized_after_completion=True, code_published=False,
                  matching_audio_audit_preserved=True, tool_sha256=sha(__file__),
                  first_archive_sha256=sha(STAGE / 'first_build_archive.json'),
                  canonical_build_sha256=sha(canonical_dir / 'build.json'),
                  regression_report_sha256=sha(regression_dir / 'report.json'),
                  window_probe_report_sha256=sha(probe_dir / 'report.json'))
    (STAGE / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'build/verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('AUDIT OK: exact GBA targets preserved; source build equal at20k; async Win32 input/stall and5k/20k WASAPI passed.')
    print('Full port, campaign save, complete mixed-PCM/ROM parity and final publication remain pending.')


if __name__ == '__main__':
    main()
