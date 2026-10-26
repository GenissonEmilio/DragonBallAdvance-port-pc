"""Boot the real translated game, then reopen its original 512-byte EEPROM."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_game_save_boot_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    stage = ROOT / 'build/next/game_save'
    build = json.loads((stage / 'build.json').read_text())
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in build[field].items()), field
    exe = stage / 'bin/dbaa_game.exe'
    assert sha(exe) == build['executable_sha256'] and not build['native_cpu_core_linked']
    sandbox = out / 'sandbox'
    sandbox.mkdir(exist_ok=True)
    rom = sandbox / 'boot.gba'
    shutil.copyfile(ROOT / 'baserom.gba', rom)
    rom_data = rom.read_bytes()
    # The original signature reader (0x080016AC) obtains its sector from a
    # ROM descriptor at [0x08001710]+2. SDK EEPROM serialization reverses the
    # eight bytes of a guest dword; the signature is not at file offset zero.
    descriptor = struct.unpack_from('<I', rom_data, 0x1710)[0] - 0x08000000
    signature_sector = rom_data[descriptor + 2]
    for suffix in ['.eep', '.sav']:
        rom.with_suffix(suffix).unlink(missing_ok=True)
    runs = []
    eeprom = None
    for index in range(3):
        tag = f'boot_{index}'
        command = [str(exe), str(rom), '--headless', '--frames', '3000',
                   '--screenshot', str(out / (tag + '.bmp')),
                   '--dump-at', '2000', str(out / (tag + '.memory')),
                   '--log-every', '1000']
        env = dict(os.environ, DBAA_GAME_AUDIO_DEVICE='0',
                   DBAA_NATIVE_REPORT=str(out / (tag + '.native.json')),
                   DBAA_GAME_AUDIO_REPORT=str(out / (tag + '.audio.json')))
        before = sha(rom.with_suffix('.eep')) if rom.with_suffix('.eep').exists() else None
        result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True, timeout=60)
        (out / (tag + '.log')).write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        assert result.returncode == 0, (index, result.returncode, result.stderr[-1400:])
        native = json.loads((out / (tag + '.native.json')).read_text())
        audio = json.loads((out / (tag + '.audio.json')).read_text())
        assert native['frames'] == 3000 and native['fallback_failures'] == 0
        assert native['rom_validated'] and not native['cpu_interpreter_compiled']
        assert audio['ok'] and not audio['whole_game_pcm_rom_equal']
        data = rom.with_suffix('.eep').read_bytes()
        (out / (tag + '.eep')).write_bytes(data)
        assert len(data) == 512, ('EEPROM capacity', len(data))
        signature_block = data[signature_sector * 8:(signature_sector + 1) * 8][::-1]
        assert struct.unpack_from('<I', signature_block)[0] == 0x9547424C, ('game signature', signature_block.hex())
        if eeprom is not None:
            assert data == eeprom, ('save rewritten on reboot', index)
        eeprom = data
        assert not rom.with_suffix('.sav').exists(), 'spurious SRAM save'
        memory = (out / (tag + '.memory')).read_bytes()
        assert len(memory) == 0x60C00
        config = struct.unpack_from('<I', memory, 0x40000 + 0x6FE4)[0]
        assert config == 0x08D2B8EC, hex(config)
        runs.append(dict(before_sha256=before, after_sha256=sha(rom.with_suffix('.eep')),
                         native=native, audio=audio, config=hex(config),
                         memory_sha256=sha(out / (tag + '.memory')),
                         screenshot_sha256=sha(out / (tag + '.bmp'))))
        print('Passed real game save boot', index + 1, '; 512 bytes and valid original signature', flush=True)
    report = dict(boots=3, frames_per_boot=3000, original_game_save_signature='0x9547424c',
                  signature_sector=signature_sector, sdk_dword_serialization='reverse eight guest bytes',
                  eeprom_bytes=512, eeprom_stable_across_reboots=True,
                  original_game_save_initialize_executed=True, gameplay_save_round_trip_validated=False,
                  native_cpu_interpreter_compiled=False, whole_game_validated=False,
                  runs=runs, executable_sha256=sha(exe), build_sha256=sha(stage / 'build.json'),
                  tool_sha256=sha(__file__))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS real native game EEPROM initialization and three reboots; campaign progress save still pending')


if __name__ == '__main__':
    main()
