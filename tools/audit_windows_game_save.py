"""Audit current EEPROM/runtime and preserve the preceding audio evidence."""
from pathlib import Path
import hashlib
import json
import re
import unittest

ROOT = Path.cwd()
STAGE = ROOT / 'build/next/game_save'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def inputs(proof, fields):
    for field in fields:
        assert all(sha(ROOT / p) == h for p, h in proof[field].items()), field


def ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from ids(test)
        else:
            yield test.id()


def main():
    legacy = ROOT / 'build/next/song_playback/audit.py'
    prefix = legacy.read_text().split('suite=unittest.defaultTestLoader.discover', 1)[0]
    assert prefix != legacy.read_text()
    exec(compile(prefix, str(legacy), 'exec'), {'__name__': 'matching_corpora_audit'})
    # Earlier input snapshots remain evidence of their own build. Changed
    # sources must have a byte-identical archived copy; they are not silently
    # relabeled as the current implementation.
    audio_stage = ROOT / 'build/next/game_audio'
    prior = read(STAGE / 'prior_verification.json')
    assert prior['stage'] == 'native_game_pcm_psg_and_window_wasapi'
    assert prior['production_functions'] == 265 and prior['production_bytes'] == 36576
    for path, digest in read(audio_stage / 'frozen_inputs.json').items():
        current = ROOT / path
        if sha(current) != digest:
            archived = audio_stage / 'frozen_sources' / path
            assert archived.is_file() and sha(archived) == digest, path
    for path, digest in prior['reports_sha256'].items():
        assert sha(ROOT / path) == digest, path
    frozen = read(STAGE / 'frozen_inputs.json')
    assert all(sha(ROOT / p) == h for p, h in frozen.items())
    build = read(STAGE / 'build.json')
    inputs(build, ['sources_sha256', 'headers_sha256', 'objects_sha256'])
    assert build['builder_sha256'] == sha(STAGE / 'build.py')
    assert build['save_atomic_replace'] and build['audio_drained_before_save']
    assert build['eeprom_dma_capacity_detection'] and build['eeprom_busy_timing_cycles'] == 115000
    assert build['native_only'] and not build['native_cpu_core_linked']
    exe = STAGE / 'bin/dbaa_game.exe'
    assert build['executable_sha256'] == sha(exe)
    symbols = (STAGE / 'bin/symbols.txt').read_text()
    assert all(n not in symbols for n in ['run_iwram_function_', 'ARMRun', 'ARMStep', 'SM83Tick', 'GBACoreCreate'])
    assert 'Dbaa_SaveWriteAtomic' in symbols and 'Dbaa_WasapiOpen' in symbols

    dma_dir = ROOT / 'build/native_eeprom_dma_validation'
    dma = read(dma_dir / 'report.json')
    assert dma['game_build_sha256'] == sha(STAGE / 'build.json')
    assert dma['capacities_kbit'] == [4, 64] and dma['erased_value_verified'] == 255
    assert dma['busy_ready_bit_verified'] and dma['dma_address_width_verified']
    assert dma['source_sha256'] == sha(ROOT / 'tools/native_eeprom_dma_probe.c')
    assert dma['tool_sha256'] == sha(ROOT / 'tools/verify_native_eeprom_dma.py')
    assert dma['executable_sha256'] == sha(dma_dir / 'eeprom_probe.exe')
    for key, size in [('4', 512), ('64', 8192)]:
        assert dma['results'][key]['bytes'] == size
        assert len(dma['results'][key]['runs']) == 3
        assert dma['results'][key]['eeprom_sha256'] == sha(dma_dir / f'sandbox_{key}/probe.eep')
    storage_dir = ROOT / 'build/native_save_storage_validation'
    storage = read(storage_dir / 'report.json')
    assert storage['process_kill_cases'] == 12 and storage['all_targets_complete']
    assert storage['writes_recover_after_kill'] and storage['read_only_failure_preserves_original']
    for field, path in [('source_sha256', 'port/windows/save_storage.c'),
                        ('header_sha256', 'port/windows/save_storage.h'),
                        ('probe_sha256', 'tools/save_storage_probe.c'),
                        ('tool_sha256', 'tools/verify_save_storage.py')]:
        assert storage[field] == sha(ROOT / path)
    assert storage['executable_sha256'] == sha(storage_dir / 'storage_probe.exe')

    boot_dir = ROOT / 'build/native_game_save_boot_validation'
    boot = read(boot_dir / 'report.json')
    assert boot['boots'] == 3 and boot['frames_per_boot'] == 3000
    assert boot['eeprom_stable_across_reboots'] and boot['eeprom_bytes'] == 512
    assert boot['signature_sector'] == 27
    assert boot['build_sha256'] == sha(STAGE / 'build.json')
    assert boot['executable_sha256'] == sha(exe)
    assert boot['tool_sha256'] == sha(ROOT / 'tools/verify_game_save_boot.py')
    for index, run in enumerate(boot['runs']):
        assert run['after_sha256'] == sha(boot_dir / f'boot_{index}.eep')
        assert run['native']['frames'] == 3000 and run['native']['fallback_failures'] == 0
    rom_dir = ROOT / 'build/native_game_save_rom_validation'
    rom = read(rom_dir / 'report.json')
    assert rom['native_boot_report_sha256'] == sha(boot_dir / 'report.json')
    assert rom['original_rom_frames'] == 6000 and rom['save_bytes'] == 512
    assert rom['erased_boot_save_rom_equal'] and rom['native_save_accepted_by_original_rom']
    assert rom['source_sha256'] == sha(ROOT / 'tools/game_save_oracle.c')
    assert rom['tool_sha256'] == sha(ROOT / 'tools/verify_game_save_rom.py')
    assert rom['oracle_executable_sha256'] == sha(rom_dir / 'oracle.exe')
    for name in ['erased', 'native_crossload']:
        assert (rom_dir / (name + '.eep')).read_bytes() == (boot_dir / 'boot_0.eep').read_bytes()
        assert rom['reports'][name]['save_sha256'] == sha(rom_dir / (name + '.eep'))

    device_dir = ROOT / 'build/native_game_save_device_validation'
    device_path = device_dir / 'report.json'
    if not device_path.exists():
        device_path = device_dir / 'failed_quality_report.json'
    device = read(device_path)
    assert device['frames'] == 5000 and device['window_backend']
    assert device['executable_sha256'] == sha(exe)
    assert device['build_report_sha256'] == sha(STAGE / 'build.json')
    assert device['tool_sha256'] == sha(ROOT / 'tools/verify_native_game_device.py')
    assert device['wasapi_submission_equals_offline_game_pcm']
    a, b = [device['reports'][key] for key in ['offline', 'wasapi']]
    assert a['native'] == b['native'] and a['pcm_sha256'] == b['pcm_sha256']
    for name, run in [('offline', a), ('wasapi', b)]:
        assert run['pcm_sha256'] == sha(device_dir / (name + '.pcm'))
        assert run['image_sha256'] == sha(device_dir / (name + '.bmp'))
    assert a['image_sha256'] == b['image_sha256'] and a['saves_after'] == b['saves_after']
    audio = b['audio']
    assert audio['device_error'] == 0 and audio['device_submitted'] == audio['stereo_samples'] == 4018026
    assert audio['pcm_fnv1a64'] == audio['device_pcm_fnv1a64'] == '044d06b01d1905e2'
    assert device['continuous_playback_passed'] == (audio['endpoint_empty'] == 0)

    campaign_dir = STAGE / 'combat_sweep20000'
    campaign = read(campaign_dir / 'run.json')
    native = read(campaign_dir / 'native.json')
    assert campaign['returncode'] == 0 and campaign['executable_sha256'] == sha(exe)
    assert native['frames'] == 20000 and native['fallback_failures'] == 0
    assert not native['cpu_interpreter_compiled']
    assert campaign['input_sha256'] == sha(campaign_dir / 'input.txt')

    log = (STAGE / 'eeprom_tests.log').read_text()
    assert re.search(r'Ran 7 tests in ', log) and '\nOK\n' in log and 'FAILED (' not in log
    historical = set(read(ROOT / 'build/next/song_playback/tests_parallel.json')['discovered'])
    discovered = set(ids(unittest.defaultTestLoader.discover('tests')))
    assert len(historical) == 514 and historical <= discovered and len(discovered) == 541
    assert len([i for i in discovered if i.startswith('test_native_eeprom.')]) == 7
    assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'input changed during audit'
    report = dict(updated='2026-10-23', stage='native_eeprom_capacity_rom_compatibility_and_atomic_storage',
                  production_functions=265, production_bytes=36576, c_functions=242, c_bytes=33856,
                  assembly_functions=23, assembly_bytes=2720, all_gba_images_rechecked=True,
                  rom_sha1=rom['rom_sha1'], last_full_suite_tests=514, tests_discovered=541,
                  current_eeprom_tests_passed=7, earlier_scoped_tests=20, full_test_suite_reexecuted=False,
                  native_game_executable=str(exe.relative_to(ROOT)), native_cpu_interpreter_compiled=False,
                  eeprom_sizes_tested=[512, 8192], eeprom_original_game_bytes=512,
                  original_rom_save_bytes_equal=True, native_save_loaded_by_original_rom=True,
                  original_rom_frames=6000, native_game_boots=3, save_process_kill_cases=12,
                  cycle_exact_eeprom_busy_validated=False, power_loss_tested=False,
                  native_game_audio_connected=True, device_frames=5000,
                  device_stereo_samples=4018026, device_pcm_equals_offline=True,
                  device_endpoint_empty=audio['endpoint_empty'],
                  device_continuity_passed=device['continuous_playback_passed'],
                  audio_producer_max_gap_us=audio['device_max_push_gap_us'],
                  audio_worker_max_gap_us=audio['device_max_render_gap_us'],
                  native_campaign_frames=20000, native_campaign_progress_save_validated=False,
                  whole_game_pcm_rom_equal=False, whole_game_validated=False, port_complete=False,
                  publication_authorized_after_completion=True,
                  publication_repository='https://github.com/GenissonEmilio/DragonBallAdvance-port-pc.git',
                  code_published=False, frozen_inputs_sha256=sha(STAGE / 'frozen_inputs.json'),
                  previous_verification_sha256=sha(STAGE / 'prior_verification.json'),
                  reports_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                                  [STAGE / 'build.json', dma_dir / 'report.json', storage_dir / 'report.json',
                                   boot_dir / 'report.json', rom_dir / 'report.json', device_path,
                                   campaign_dir / 'run.json', campaign_dir / 'native.json']})
    (STAGE / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (ROOT / 'build/verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('EVIDENCE AUDIT OK: 265 GBA images; 512-byte original-ROM save; three native boots; DMA/atomic storage; 7 scoped tests.')
    print('Audio continuity passed:', device['continuous_playback_passed'], '; complete port: False; publishing pending completion.')


if __name__ == '__main__':
    main()
