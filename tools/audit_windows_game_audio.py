"""Audit matching code, native-game audio, scoped tests and real WASAPI output."""
from pathlib import Path
import hashlib
import json
import re
import unittest

ROOT = Path.cwd()
STAGE = ROOT / 'build/next/game_audio'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def check_inputs(proof, fields):
    for field in fields:
        assert all(sha(ROOT / p) == h for p, h in proof[field].items()), field


def identifiers(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from identifiers(test)
        else:
            yield test.id()


def main():
    # The historical audit's prefix rechecks every whole GBA ELF section and
    # native corpus. Its later discovery assertion describes the former suite.
    legacy = ROOT / 'build/next/song_playback/audit.py'
    prefix = legacy.read_text().split('suite=unittest.defaultTestLoader.discover', 1)[0]
    assert prefix != legacy.read_text()
    exec(compile(prefix, str(legacy), 'exec'), {'__name__': 'baseline_audit'})
    baseline = read(ROOT / 'build/next/song_playback/audit.json')
    assert baseline['production_functions'] == 265 and baseline['production_bytes'] == 36576
    frozen_path = STAGE / 'frozen_inputs.json'
    frozen = read(frozen_path)
    assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'current frozen input changed'

    chip_dir = ROOT / 'build/native_psg_bias_validation'
    chip, chip_build = read(chip_dir / 'report.json'), read(chip_dir / 'build.json')
    check_inputs(chip_build, ['sources_sha256', 'headers_sha256', 'objects_sha256'])
    assert chip_build['builder_sha256'] == sha(ROOT / 'tools/build_native_psg.py')
    assert not chip_build['cpu_cores_linked'] and not chip_build['cpu_core_macros_enabled']
    assert not chip['quick'] and chip['stereo_samples'] == 160000 and chip['writes'] == 1490
    assert chip['raw_digital_psg_equal'] and chip['nr52_equal']
    assert chip['tool_sha256'] == sha(ROOT / 'tools/verify_native_psg.py')
    assert chip['adapter_sha256'] == sha(ROOT / 'port/audio/psg_mgba.c')
    assert chip['oracle_sha256'] == sha(ROOT / 'tools/psg_oracle.c')
    assert chip['native_library_sha256'] == sha(chip_dir / 'psg.dll')
    assert chip['oracle_library_sha256'] == sha(chip_dir / 'oracle.dll')

    wrap_dir = ROOT / 'build/native_psg_wrap_validation'
    wrap = read(wrap_dir / 'report.json')
    assert wrap['stereo_snapshots'] == 4040 and wrap['nonzero_snapshots'] == 4020
    assert wrap['raw_digital_psg_equal'] and wrap['nr52_equal']
    assert wrap['chip_build_sha256'] == sha(chip_dir / 'build.json')
    assert wrap['chip_report_sha256'] == sha(chip_dir / 'report.json')
    assert wrap['tool_sha256'] == sha(ROOT / 'tools/verify_psg_wrap.py')

    mix_dir = ROOT / 'build/native_digital_mixer_validation'
    mix = read(mix_dir / 'report.json')
    assert not mix['quick'] and mix['cases'] == 150528 and mix['original_mgba_mix_calls'] == 37632
    assert mix['pcm16_equal_to_original_digital_mix']
    for field, path in [('source_sha256', 'port/audio/digital_mixer.c'),
                        ('header_sha256', 'port/include/digital_mixer.h'),
                        ('oracle_source_sha256', 'tools/digital_mixer_oracle.c'),
                        ('tool_sha256', 'tools/verify_digital_mixer.py')]:
        assert mix[field] == sha(ROOT / path), field
    assert mix['library_sha256'] == sha(mix_dir / 'mixer.dll')
    assert mix['oracle_library_sha256'] == sha(mix_dir / 'oracle.dll')

    consumer_dir = ROOT / 'build/native_game_audio_validation'
    consumer = read(consumer_dir / 'report.json')
    assert not consumer['quick'] and consumer['frames'] == 1800
    assert consumer['pcm16_equal_to_immutable_rom_corpus']
    assert consumer['source_pcm8_original_rom_validation_inherited']
    assert consumer['source_pcm8_digest'] == '3d8b28801deac7d450790a8a893d8e19c09a3a6316c123d915569b6080952006'
    assert consumer['stereo_samples'] == 1446569
    assert consumer['pcm16_sha256'] == sha(consumer_dir / 'game.pcm') == baseline['song_pcm16_sha256']
    assert consumer['pcm16_fnv1a64'] == '051f790bb9359803'
    assert consumer['tool_sha256'] == sha(ROOT / 'tools/verify_game_audio_pcm.py')
    check_inputs(consumer['native_build'], ['sources_sha256', 'objects_sha256'])
    assert consumer['native_build']['library_sha256'] == sha(consumer_dir / 'consumer.dll')
    assert not consumer['whole_game_pcm_rom_equal'] and not consumer['psg_song_rom_equal']

    build = read(STAGE / 'build.json')
    check_inputs(build, ['sources_sha256', 'headers_sha256', 'objects_sha256'])
    assert build['native_only'] and build['game_audio_connected'] and not build['native_cpu_core_linked']
    exe = STAGE / 'bin/dbaa_game.exe'
    assert build['executable_sha256'] == sha(exe)
    symbols = (STAGE / 'bin/symbols.txt').read_text()
    assert all(n not in symbols for n in ['run_iwram_function_', 'ARMRun', 'ARMStep', 'SM83Tick', 'GBACoreCreate'])
    assert all(n in symbols for n in ['Dbaa_GameAudioAdvance', 'Dbaa_WasapiOpen', 'Dbaa_WindowPace'])

    device_dir = ROOT / 'build/native_game_window_audio_final_validation'
    device_report = device_dir / 'report.json'
    if not device_report.exists():
        device_report = device_dir / 'failed_quality_report.json'
    device = read(device_report)
    assert device['frames'] == 5000 and device['window_backend'] and device['window_hidden']
    assert device['executable_sha256'] == sha(exe)
    assert device['build_report_sha256'] == sha(STAGE / 'build.json')
    assert device['tool_sha256'] == sha(ROOT / 'tools/verify_native_game_device.py')
    assert device['wasapi_submission_equals_offline_game_pcm'] and device['original_song_pcm_corpus_equal']
    a, b = [device['reports'][name] for name in ['offline', 'wasapi']]
    assert a['native'] == b['native'] and a['native']['frames'] == 5000
    assert a['pcm_sha256'] == b['pcm_sha256']
    for name, result in [('offline', a), ('wasapi', b)]:
        assert result['pcm_sha256'] == sha(device_dir / (name + '.pcm'))
        assert result['image_sha256'] == sha(device_dir / (name + '.bmp'))
    assert a['image_sha256'] == b['image_sha256'] and a['saves_after'] == b['saves_after']
    audio = b['audio']
    assert audio['device_submitted'] == audio['stereo_samples'] == 4018027
    assert audio['pcm_fnv1a64'] == audio['device_pcm_fnv1a64'] == '878b77d164258400'
    assert audio['device_error'] == audio['device_queue_remaining'] == 0
    continuous = audio['endpoint_empty'] == 0
    assert device['continuous_playback_passed'] == continuous
    assert audio['device_mmcss'] == 1 and not audio['whole_game_pcm_rom_equal']

    save_dir = ROOT / 'build/native_save_persistence_validation'
    save = read(save_dir / 'report.json')
    assert save['persistence_equal'] and save['blocks'] == 1024 and save['bytes'] == 8192
    assert save['process_runs'] == 3 and not save['game_save_round_trip_validated']
    assert not save['busy_timing_validated'] and not save['hardware_erased_value_validated']
    assert save['game_build_sha256'] == sha(STAGE / 'build.json')
    assert save['source_sha256'] == sha(ROOT / 'tools/native_save_probe.c')
    assert save['tool_sha256'] == sha(ROOT / 'tools/verify_native_save_persistence.py')
    assert save['executable_sha256'] == sha(save_dir / 'save_probe.exe')
    assert save['eeprom_sha256'] == sha(save_dir / 'sandbox/probe.eep')

    long_native = read(STAGE / 'campaign_audio20000.native.json')
    long_audio = read(STAGE / 'campaign_audio20000.audio.json')
    assert long_native['frames'] == 20000 and long_native['fallback_failures'] == 0
    assert long_audio['ok'] and long_audio['cycles'] == 5617836829 > 2**32
    assert not long_audio['device_enabled'] and not long_audio['whole_game_pcm_rom_equal']
    assert long_audio['stereo_samples'] == 16072760
    # The runner completed the child but failed to save its Python log due to
    # a redirect collision. These are direct native outputs, not a recovered
    # process return code. Preserve that limitation instead of rerunning it.
    assert 'PermissionError' in (STAGE / 'campaign_audio20000.log').read_text()

    logs = [('build/next/native_game/irq_tests.log', 6),
            ('build/next/game_audio/psg_bias_tests.log', 6),
            ('build/next/game_audio/consumer_mixer_tests.log', 8)]
    for path, count in logs:
        text = (ROOT / path).read_text()
        assert re.search(rf'Ran {count} tests? in ', text) and '\nOK\n' in text
        assert 'FAILED (' not in text
    current = set(identifiers(unittest.defaultTestLoader.discover('tests')))
    historical = set(read(ROOT / 'build/next/song_playback/tests_parallel.json')['discovered'])
    assert len(historical) == 514 and historical <= current
    added = current - historical
    assert len(current) == 534 and len(added) == 20
    assert all(n.startswith(('test_native_irq.', 'test_native_psg.', 'test_game_audio_pcm.',
                             'test_native_digital_mixer.')) for n in added)
    assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'input changed during audit'

    result = dict(updated='2026-10-22', stage='native_game_pcm_psg_and_window_wasapi',
                  rom_sha1=hashlib.sha1((ROOT / 'baserom.gba').read_bytes()).hexdigest(),
                  rom_sha256=sha(ROOT / 'baserom.gba'),
                  production_functions=265, production_bytes=36576, c_functions=242, c_bytes=33856,
                  assembly_functions=23, assembly_bytes=2720, native_audio_helper_targets=66,
                  all_265_gba_images_rechecked=True, native_corpora_reexecuted=0,
                  historical_native_corpora_reaudited=25, last_full_suite_tests=514,
                  full_test_suite_reexecuted=False, tests_discovered=534, current_scoped_tests=20,
                  scoped_tests_passed=20, native_game_audio_connected=True,
                  native_game_executable=str(exe.relative_to(ROOT)), native_cpu_interpreter_compiled=False,
                  original_song_frames=1800, original_song_stereo_samples=1446569,
                  original_song_consumer_pcm_rom_equal=True, psg_digital_samples=160000,
                  psg_writes=1490, psg_rollover_snapshots=4040, digital_mix_cases=150528,
                  window_game_frames=5000, game_wasapi_stereo_samples=4018027,
                  game_device_pcm_equals_offline=True, game_device_endpoint_empty=audio['endpoint_empty'],
                  game_device_continuous_playback_passed=continuous,
                  game_device_mmcss=True, whole_game_pcm_rom_equal=False,
                  earlier_device_playback_gaps_observed=True,
                  observed_native_long_frames=20000, observed_native_long_cycles=long_audio['cycles'],
                  native_long_process_returncode_observed=False, native_long_runner_log_write_failed=True,
                  eeprom_persistence_blocks=1024, eeprom_persistence_processes=3,
                  gameplay_save_roundtrip_validated=False, eeprom_busy_timing_validated=False,
                  whole_game_validated=False, port_complete=False,
                  human_speaker_audibility_confirmed=False, analog_output_bit_exact=False,
                  audio_queue_feedback_enabled=True, long_term_clock_validation=False,
                  frozen_inputs=len(frozen), frozen_inputs_sha256=sha(frozen_path),
                  prior_verification_sha256=sha(STAGE / 'prior_verification.json'),
                  reports_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                                  [chip_dir / 'report.json', wrap_dir / 'report.json', mix_dir / 'report.json',
                                   consumer_dir / 'report.json', device_report, STAGE / 'build.json',
                                   save_dir / 'report.json', STAGE / 'campaign_audio20000.native.json',
                                   STAGE / 'campaign_audio20000.audio.json']})
    (STAGE / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'build/verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('EVIDENCE AUDIT OK: 265 whole GBA sections; ROM PCM corpus; PSG/bias/rollover; digital mix; 5000 Win32/WASAPI frames; 20 scoped tests.')
    print('Continuous device playback passed:', continuous, '; port complete: False')


if __name__ == '__main__':
    main()
