"""Write/read/reopen all EEPROM blocks using the actual native runtime objects."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_save_persistence_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    proof_path = ROOT / 'build/next/game_audio/build.json'
    proof = json.loads(proof_path.read_text())
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in proof[field].items()), field
    assert proof['native_only'] and not proof['native_cpu_core_linked']
    objects = []
    for name in proof['objects_sha256']:
        path = ROOT / name
        if path.name == 'native_bridge.o':
            copy = out / 'bridge_probe.o'
            subprocess.run([str(gcc.with_name('objcopy.exe')), '--redefine-sym',
                            'main=Dbaa_GameEntryMain', str(path), str(copy)], check=True)
            path = copy
        objects.append(path)
    generated = ROOT / 'build/next/native_game/generated'
    command = [str(gcc), '-std=c11', '-O2', '-DGBA_NO_SDL', '-I' + str(generated),
               str(ROOT / 'tools/native_save_probe.c'), *map(str, objects),
               '-Wl,--stack,16777216', '-o', str(out / 'save_probe.exe'),
               '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    sandbox = out / 'sandbox'
    sandbox.mkdir(exist_ok=True)
    rom = sandbox / 'probe.gba'
    shutil.copyfile(ROOT / 'baserom.gba', rom)
    for suffix in ['.eep', '.sav']:
        rom.with_suffix(suffix).unlink(missing_ok=True)
    runs = []
    for mode in ['write', 'read', 'read']:
        result = subprocess.run([str(out / 'save_probe.exe'), mode, str(rom)],
                                capture_output=True, text=True, timeout=30)
        (out / f'run_{len(runs)}.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        runs.append(json.loads(result.stdout.strip().splitlines()[-1]))
        data = rom.with_suffix('.eep').read_bytes()
        expected = bytes((i * 73 + ((i >> 3) ^ 0xA5) * 19 + 0x37) & 255 for i in range(8192))
        assert data == expected, 'serialized EEPROM bytes differ from the independent payload'
    report = dict(blocks=1024, bytes=8192, process_runs=3, persistence_equal=True,
                  native_cpu_interpreter_compiled=False, translated_game_functions_executed=False,
                  game_save_round_trip_validated=False, busy_timing_validated=False,
                  hardware_erased_value_validated=False, gba_byte_matching=False,
                  eeprom_sha256=sha(rom.with_suffix('.eep')), runs=runs,
                  game_build_sha256=sha(proof_path), executable_sha256=sha(out / 'save_probe.exe'),
                  source_sha256=sha(ROOT / 'tools/native_save_probe.c'), tool_sha256=sha(__file__))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS native EEPROM persistence: 1024 blocks, 8192 bytes, three processes; gameplay save validation pending')


if __name__ == '__main__':
    main()
