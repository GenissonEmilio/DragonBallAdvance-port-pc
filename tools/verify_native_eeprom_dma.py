"""Verify both DMA-selected EEPROM capacities, erased bytes, busy and reopen."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_eeprom_dma_validation')
    parser.add_argument('--game-stage', type=Path, default=ROOT / 'build/next/game_save')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    proof_path = args.game_stage.resolve() / 'build.json'
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
               str(ROOT / 'tools/native_eeprom_dma_probe.c'), *map(str, objects),
               '-Wl,--stack,16777216', '-o', str(out / 'eeprom_probe.exe'),
               '-lm', '-lgdi32', '-luser32', '-lole32', '-luuid', '-lavrt']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    results = {}
    for capacity, size in [(4, 512), (64, 8192)]:
        sandbox = out / f'sandbox_{capacity}'
        sandbox.mkdir(exist_ok=True)
        rom = sandbox / 'probe.gba'
        shutil.copyfile(ROOT / 'baserom.gba', rom)
        for suffix in ['.eep', '.sav']:
            rom.with_suffix(suffix).unlink(missing_ok=True)
        runs = []
        for mode in ['write', 'read', 'read']:
            result = subprocess.run([str(out / 'eeprom_probe.exe'), mode, str(capacity), str(rom)],
                                    capture_output=True, text=True, timeout=60)
            (out / f'run_{capacity}_{len(runs)}.log').write_text(result.stdout + result.stderr)
            assert result.returncode == 0, result.stdout + result.stderr
            run = json.loads(result.stdout.strip().splitlines()[-1])
            assert run['ok'] and run['capacity_kbit'] == capacity
            if mode == 'write':
                assert run['busy_polls'] > 0
            runs.append(run)
            data = rom.with_suffix('.eep').read_bytes()
            expected = bytes((i * 73 + ((i >> 3) ^ 0xA5) * 19 + 0x37) & 255 for i in range(size))
            assert data == expected, 'serialized capacity/payload mismatch'
            assert not rom.with_suffix('.sav').exists(), 'EEPROM cart emitted a spurious SRAM save'
        results[str(capacity)] = dict(bytes=size, runs=runs, eeprom_sha256=sha(rom.with_suffix('.eep')))
    report = dict(capacities_kbit=[4, 64], persistence_equal=True, dma_address_width_verified=True,
                  erased_value_verified=255, busy_ready_bit_verified=True,
                  native_cpu_interpreter_compiled=False, translated_game_functions_executed=False,
                  game_save_round_trip_validated=False, cycle_exact_busy_timing_validated=False,
                  gba_byte_matching=False, results=results, game_build_sha256=sha(proof_path),
                  executable_sha256=sha(out / 'eeprom_probe.exe'),
                  source_sha256=sha(ROOT / 'tools/native_eeprom_dma_probe.c'), tool_sha256=sha(__file__))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS native DMA3 EEPROM: 4/64 Kbit, 512/8192 bytes, erased FF, busy and six processes; gameplay save validation pending')


if __name__ == '__main__':
    main()
