"""Audit unchanged PCM and state under the new frame-producer scheduler."""
from pathlib import Path
import hashlib
import json
import re
import unittest

ROOT = Path.cwd()
STAGE = ROOT / 'build/next/game_timing'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from tests(item)
        else:
            yield item.id()


def main():
    legacy = ROOT / 'build/next/song_playback/audit.py'
    prefix = legacy.read_text().split('suite=unittest.defaultTestLoader.discover', 1)[0]
    exec(compile(prefix, str(legacy), 'exec'), {'__name__': 'matching_audit'})
    previous_stage = ROOT / 'build/next/game_save'
    prior = read(previous_stage / 'audit.json')
    assert prior['production_functions'] == 265 and prior['production_bytes'] == 36576
    for path, digest in read(previous_stage / 'frozen_inputs.json').items():
        if sha(ROOT / path) != digest:
            assert sha(previous_stage / 'frozen_sources' / path) == digest, path
    for path, digest in prior['reports_sha256'].items():
        assert sha(ROOT / path) == digest, path
    frozen = read(STAGE / 'frozen_inputs.json')
    assert all(sha(ROOT / p) == h for p, h in frozen.items())
    build = read(STAGE / 'build.json')
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in build[field].items()), field
    assert build['games_mmcss_requested'] and not build['native_cpu_core_linked']
    assert build['builder_sha256'] == sha(STAGE / 'build.py')
    assert build['previous_build_sha256'] == sha(previous_stage / 'build.json')
    exe = STAGE / 'bin/dbaa_game.exe'
    assert build['executable_sha256'] == sha(exe)
    symbols = (STAGE / 'bin/symbols.txt').read_text()
    assert all(n not in symbols for n in ['run_iwram_function_', 'ARMRun', 'ARMStep', 'SM83Tick', 'GBACoreCreate'])
    sessions = {}
    for folder, frames, samples, digest in [
            ('native_game_timing_device_validation', 5000, 4018026, '044d06b01d1905e2'),
            ('native_game_timing_long_validation', 20000, 16072761, '199d7f590635ad76')]:
        directory = ROOT / 'build' / folder
        proof = read(directory / 'report.json')
        assert proof['frames'] == frames and proof['window_backend'] and proof['window_hidden']
        assert proof['executable_sha256'] == sha(exe)
        assert proof['build_report_sha256'] == sha(STAGE / 'build.json')
        assert proof['tool_sha256'] == sha(ROOT / 'tools/verify_native_game_device.py')
        assert proof['continuous_playback_passed'] and proof['wasapi_submission_equals_offline_game_pcm']
        a, b = [proof['reports'][name] for name in ['offline', 'wasapi']]
        assert a['native'] == b['native'] and a['native']['frames'] == frames
        assert a['image_sha256'] == b['image_sha256'] and a['saves_after'] == b['saves_after']
        for name, run in [('offline', a), ('wasapi', b)]:
            assert run['pcm_sha256'] == sha(directory / (name + '.pcm'))
            assert run['image_sha256'] == sha(directory / (name + '.bmp'))
        assert a['pcm_sha256'] == b['pcm_sha256']
        audio = b['audio']
        assert audio['ok'] and audio['device_submitted'] == audio['stereo_samples'] == samples
        assert audio['pcm_fnv1a64'] == audio['device_pcm_fnv1a64'] == digest
        assert audio['endpoint_empty'] == audio['device_error'] == audio['device_queue_remaining'] == 0
        assert audio['device_mmcss'] == 1
        assert '[window] Games MMCSS active' in (directory / 'wasapi.log').read_text()
        assert not proof['whole_game_pcm_rom_equal'] and not proof['whole_game_validated']
        sessions[str(frames)] = dict(stereo_samples=samples, pcm_fnv1a64=digest,
                                    report_sha256=sha(directory / 'report.json'),
                                    producer_gap_max_us=audio['device_max_push_gap_us'],
                                    worker_gap_max_us=audio['device_max_render_gap_us'],
                                    seconds=b['seconds'])
    log = (STAGE / 'eeprom_tests.log').read_text()
    assert re.search(r'Ran 7 tests in ', log) and '\nOK\n' in log and 'FAILED (' not in log
    discovered = set(tests(unittest.defaultTestLoader.discover('tests')))
    historical = set(read(ROOT / 'build/next/song_playback/tests_parallel.json')['discovered'])
    assert len(discovered) == 541 and len(historical) == 514 and historical <= discovered
    discovery = read(ROOT / 'build/native_generation_discovery/discovery.json')
    assert discovery['combined_candidates'] == 2364 and discovery['tables'] == 455
    assert discovery['pointer_candidates'] == 136 and discovery['jump_table_candidates'] == 2228
    assert discovery['tool_sha256'] == sha(ROOT / 'tools/discover_native_entries.py')
    new = {int(x, 0) for x in (ROOT / 'build/native_generation_discovery/extra_entries.txt').read_text().split()}
    old = {int(x, 0) for x in (ROOT / 'build/next/native_game/extra_entries.txt').read_text().split()}
    assert new == old and not discovery['hints_are_verified_code']
    assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'input changed during audit'
    report = dict(updated='2026-10-23', stage='native_game_frame_producer_mmcss_and_long_wasapi',
                  production_functions=265, production_bytes=36576, c_functions=242, c_bytes=33856,
                  assembly_functions=23, assembly_bytes=2720, all_gba_images_rechecked=True,
                  native_cpu_interpreter_compiled=False, native_game_executable=str(exe.relative_to(ROOT)),
                  original_song_pcm_rom_corpus_preserved=True, original_save_rom_bytes_equal=True,
                  game_device_pcm_equals_offline=True, game_device_continuity_passed=True,
                  games_mmcss_active=True, pro_audio_mmcss_active=True, sessions=sessions,
                  longest_device_frames=20000, game_device_endpoint_empty=0,
                  last_full_suite_tests=514, tests_discovered=541, current_eeprom_tests_passed=7,
                  full_test_suite_reexecuted=False, original_native_corpora_reexecuted=0,
                  earlier_scoped_tests_preserved=20, historical_corpora_reaudited=25,
                  candidate_discovery_reproduced=True, candidate_discovery_entries=2364,
                  whole_game_pcm_rom_equal=False, campaign_progress_save_validated=False,
                  clean_game_build_validated=False, whole_game_validated=False, port_complete=False,
                  publication_authorized_after_completion=True,
                  publication_repository='https://github.com/GenissonEmilio/DragonBallAdvance-port-pc.git',
                  code_published=False, previous_verification_sha256=sha(previous_stage / 'audit.json'),
                  frozen_inputs_sha256=sha(STAGE / 'frozen_inputs.json'),
                  build_sha256=sha(STAGE / 'build.json'), tests_log_sha256=sha(STAGE / 'eeprom_tests.log'))
    (STAGE / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'build/verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('EVIDENCE AUDIT OK: exact GBA matching preserved; 5k/20k real WASAPI sessions, zero endpoint empties; state/PCM/save equal offline.')
    print('Full game, clean build, campaign save and final publication remain incomplete.')


if __name__ == '__main__':
    main()
