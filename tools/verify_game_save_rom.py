"""Compare original-ROM save bytes with native boot and cross-load them."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_game_save_rom_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    native_dir = ROOT / 'build/native_game_save_boot_validation'
    boot = json.loads((native_dir / 'report.json').read_text())
    assert boot['boots'] == 3 and boot['eeprom_stable_across_reboots']
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    mgba = ROOT / 'tools/local/mgba_reference'
    configured = ROOT / 'build/next/psg_reference/mgba_build'
    definitions = ['BUILD_STATIC', 'ENABLE_DIRECTORIES', 'ENABLE_VFS', 'ENABLE_VFS_FD',
                   'M_CORE_GB', 'M_CORE_GBA', '_GNU_SOURCE', '_FILE_OFFSET_BITS=64']
    command = [str(gcc), '-std=c11', '-O2', *['-D' + n for n in definitions],
               *['-I' + str(p) for p in [mgba / 'include', configured / 'include', mgba / 'src']],
               str(ROOT / 'tools/game_save_oracle.c'), str(configured / 'libmgba.a'),
               '-o', str(out / 'oracle.exe'), '-lws2_32', '-lshlwapi', '-lm', '-lole32', '-luuid']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    reports = {}
    for name, seed in [('erased', None), ('native_crossload', native_dir / 'boot_0.eep')]:
        command = [str(out / 'oracle.exe'), str(ROOT / 'baserom.gba'), '3000',
                   str(out / (name + '.eep')), str(out / (name + '.memory'))]
        if seed:
            command.append(str(seed))
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (out / (name + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout.strip().splitlines()[-1])
        assert report['ok'] and report['save_bytes'] == 512
        expected = (native_dir / 'boot_0.eep').read_bytes()
        actual = (out / (name + '.eep')).read_bytes()
        if actual != expected:
            differences = [i for i, (a, b) in enumerate(zip(actual, expected)) if a != b]
            failure = dict(case=name, different_bytes=len(differences), offsets=differences,
                           native_sha256=sha(native_dir / 'boot_0.eep'), rom_sha256=sha(out / (name + '.eep')))
            (out / 'failed_case.json').write_text(json.dumps(failure, indent=2) + '\n')
            raise AssertionError(failure)
        reports[name] = dict(reference=report, save_sha256=sha(out / (name + '.eep')),
                             memory_sha256=sha(out / (name + '.memory')))
        print('Passed original ROM EEPROM case:', name, '; 512 bytes equal', flush=True)
    report = dict(rom_sha1=hashlib.sha1((ROOT / 'baserom.gba').read_bytes()).hexdigest(),
                  save_bytes=512, erased_boot_save_rom_equal=True, native_save_accepted_by_original_rom=True,
                  original_rom_executed=True, original_rom_frames=6000,
                  native_cpu_interpreter_compiled=False, gameplay_progress_save_validated=False,
                  whole_game_state_equal=False, reports=reports,
                  native_boot_report_sha256=sha(native_dir / 'report.json'),
                  source_sha256=sha(ROOT / 'tools/game_save_oracle.c'), tool_sha256=sha(__file__),
                  oracle_executable_sha256=sha(out / 'oracle.exe'),
                  original_mgba_library_sha256=sha(configured / 'libmgba.a'))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS native/original ROM save bytes and native-to-ROM cross-load; campaign progress pending')


if __name__ == '__main__':
    main()
