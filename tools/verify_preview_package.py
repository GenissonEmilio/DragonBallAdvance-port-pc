"""Check an extracted Windows preview and real launcher with an isolated ROM."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--rom', type=Path, default=ROOT / 'baserom.gba')
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve earlier verification outputs'
    out.mkdir(parents=True)
    archive = args.archive.resolve()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(Path(n).suffix.lower() in {'.gba', '.sav', '.eep', '.bios', '.pcm', '.wav', '.bmp'} for n in z.namelist())
        assert all('..' not in Path(n).parts and not Path(n).is_absolute() for n in z.namelist())
        z.extractall(out / 'folder with spaces')
    package = next((out / 'folder with spaces').iterdir())
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert all(sha(package / n) == h for n, h in manifest['files_sha256'].items())
    romdir = out / 'local rom'
    romdir.mkdir()
    rom = romdir / 'test game.gba'
    shutil.copyfile(args.rom, rom)
    assert hashlib.sha1(rom.read_bytes()).hexdigest() == manifest['rom_sha1']
    binary = (package / 'dbaa_game.exe').read_bytes()
    data = rom.read_bytes()
    checked = 0
    for off in range(0x180000, len(data) - 65536, 65536):
        block = data[off:off + 65536]
        if len(set(block)) > 64:
            assert block not in binary, hex(off)
            checked += 1
    command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               str(package / 'Iniciar.ps1'), '-Rom', str(rom), '-Frames', '300', '-Headless', '-NoAudio']
    run = subprocess.run(command, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    # Windows PowerShell writes in the active Windows code page. Preserve bytes.
    (out / 'launcher.stdout.log').write_bytes(run.stdout)
    (out / 'launcher.stderr.log').write_bytes(run.stderr)
    assert run.returncode == 0, repr(run.stdout + run.stderr)
    sessions = [p for p in (package / 'logs').iterdir() if p.is_dir()]
    assert len(sessions) == 1
    native = json.loads((sessions[0] / 'native.json').read_text())
    audio = json.loads((sessions[0] / 'audio.json').read_text())
    assert native['frames'] == 300 and native['fallback_failures'] == 0 and not native['cpu_interpreter_compiled']
    assert audio['ok'] and not audio['device_enabled']
    assert rom.with_suffix('.eep').stat().st_size == 512
    bad = romdir / 'wrong.gba'
    bad.write_bytes(b'not a ROM')
    negative = list(command)
    negative[negative.index('-Rom') + 1] = str(bad)
    result = subprocess.run(negative, capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 2
    assert len([p for p in (package / 'logs').iterdir() if p.is_dir()]) == 1
    report = dict(zip_crc_valid=True, all_manifest_file_hashes_equal=True,
                  archive_sha256=sha(archive), executable_sha256=sha(package / 'dbaa_game.exe'),
                  rom_bios_saves_assets_in_archive=False,
                  nontrivial_64k_rom_resource_blocks_not_embedded=checked,
                  launcher_from_extracted_zip_passed=True, paths_with_spaces_passed=True,
                  headless_frames=300, audio_device_disabled_for_launcher_smoke=True,
                  eeprom_created_bytes=512, invalid_rom_rejected_exit_code=2,
                  source_sha256=sha(__file__), whole_game_validated=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
