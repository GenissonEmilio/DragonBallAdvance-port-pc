"""Audit BIOS math, preserved prior evidence, and the fresh native-game build."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    out = ROOT / 'build/next/bios_math'
    out.mkdir(parents=True, exist_ok=True)
    legacy = ROOT / 'build/next/song_playback/audit.py'
    exec(compile(legacy.read_text().split('suite=unittest.defaultTestLoader.discover', 1)[0], str(legacy), 'exec'), {})
    prior = ROOT / 'build/next/shift_flags'
    frozen = json.loads((prior / 'frozen_inputs.json').read_text())
    assert len(frozen) == 331
    changed = []
    for path, digest in frozen.items():
        assert sha(prior / 'source_copies' / path) == digest
        if sha(ROOT / path) != digest:
            changed.append(path)
    old_audit = json.loads((prior / 'audit.json').read_text())
    assert old_audit['instruction_cases'] == 405376 and old_audit['instruction_mismatches'] == 0
    reference = ROOT / 'build/native_bios_math_validation_v5'
    math = json.loads((reference / 'report.json').read_text())
    assert math['cases'] == 196833 and math['arctan_cases'] == 65536 and math['arctan2_cases'] == 131297
    assert math['registers_equal'] and math['mismatches'] == 0 and math['old_arctan2_positive_x_axis'] == 0x8000
    assert sha(reference / 'bios_math.h') == sha(ROOT / 'port/include/bios_math.h') == math['header_sha256']
    assert sha(reference / 'tool_snapshot.py') == sha(ROOT / 'tools/verify_bios_math.py') == math['tool_sha256']
    assert sha(reference / 'oracle_source.c') == sha(ROOT / 'tools/bios_math_oracle.c') == math['oracle_source_sha256']
    assert sha(reference / 'native.bin') == sha(reference / 'oracle.bin') == math['actual_sha256'] == math['expected_sha256']
    actual_dir = ROOT / 'build/native_bios_math_runtime_validation'
    actual = json.loads((actual_dir / 'report.json').read_text())
    assert actual['runtime_swi_registers_equal'] and actual['cases'] == 196833
    assert actual['runtime_source_sha256'] == sha(ROOT / 'tools/local/sp00nz_gbarecomp/src/runtime.c')
    assert actual['header_sha256'] == math['header_sha256']
    assert sha(actual_dir / 'actual.bin') == math['expected_sha256'] == actual['actual_sha256']
    assert not actual['cycles_compared'] and not math['physical_bios_compared']
    game = ROOT / 'build/windows_native_bios'
    build = json.loads((game / 'build.json').read_text())
    assert len(build['compile']) == 108 and all(not row['cached'] for row in build['compile'].values())
    assert not build['native_cpu_core_linked'] and not build['historical_objects_reused']
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in build[field].items()), field
    assert sha(game / 'bin/dbaa_game.exe') == build['executable_sha256']
    old = json.loads((ROOT / 'build/windows_native_shift/build.json').read_text())
    old_objects = {Path(p).name: h for p, h in old['objects_sha256'].items()}
    new_objects = {Path(p).name: h for p, h in build['objects_sha256'].items()}
    assert [n for n in new_objects if new_objects[n] != old_objects[n]] == ['runtime.o']
    assert new_objects['runtime.o'] == actual['runtime_object_sha256']
    regression_path = ROOT / 'build/native_bios_build_regression/report.json'
    regression = json.loads(regression_path.read_text())
    assert regression['frames'] == 20000
    assert all(regression[k] for k in ['memory_bytes_equal', 'image_bytes_equal', 'pcm_bytes_equal', 'save_bytes_equal'])
    device_path = ROOT / 'build/native_bios_game_device_validation_v3/report.json'
    device = json.loads(device_path.read_text())
    assert device['continuous_playback_passed'] and device['frames'] == 5000
    assert device['executable_sha256'] == build['executable_sha256']
    assert device['reports']['wasapi']['audio']['endpoint_empty'] == 0
    failure_path = ROOT / 'build/native_bios_game_device_validation_v2/failed_quality_report.json'
    failure = json.loads(failure_path.read_text())
    assert not failure['continuous_playback_passed']
    assert failure['reports']['wasapi']['audio']['endpoint_empty'] == 50
    assert failure['wasapi_submission_equals_offline_game_pcm']
    patch = ROOT / 'tools/patches/gbarecomp-native.patch'
    subprocess.run(['git', '-C', str(ROOT / 'tools/local/sp00nz_gbarecomp'), 'apply', '--reverse', '--check', str(patch)], check=True)
    report = dict(software_bios_math_cases=196833, math_output_bytes=196833*16, math_registers_equal=True,
                  actual_runtime_object_tested=True, other_107_objects_equal_prior=True, clean_source_objects=108,
                  prior_isa_instruction_cases=405376, prior_isa_mismatches=0, prior_sources_preserved=len(frozen),
                  production_functions=265, production_bytes=36576, native_audio_corpora_preserved=25,
                  native_cpu_interpreter_compiled=False, regression_frames=20000,
                  regression_memory_image_pcm_save_equal=True, device_frames=5000, device_endpoint_empty=0,
                  software_bios_reference=True, physical_bios_compared=False, bios_cycles_validated=False,
                  whole_game_pcm_rom_equal=False, campaign_progress_save_validated=False,
                  whole_game_validated=False, port_complete=False, changed_prior_inputs=changed,
                  prior_loaded_device_failure_preserved=True, prior_loaded_device_empty=50,
                  prior_loaded_device_failure_sha256=sha(failure_path),
                  prior_loaded_test_conditions=['NTFS-compressed executable', 'artifact compression/hashing', 'headless campaign test'],
                  precise_cause_of_prior_device_failure_established=False,
                  executable_sha256=build['executable_sha256'], patch_sha256=sha(patch), tool_sha256=sha(__file__),
                  references_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                    [reference / 'report.json', actual_dir / 'report.json', regression_path, device_path, game / 'build.json']})
    (out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS native BIOS math integration, preserved matching/audio/ISA and game regression/device')


if __name__ == '__main__':
    main()
