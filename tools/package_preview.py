"""Package a tested native preview without ROM, BIOS, saves or game assets."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'https://github.com/GenissonEmilio/DragonBallAdvance-port-pc'
MGBA_PIN = 'fd9dc5c2cbf234365068855851107e762fc6211b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--validation', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve earlier packages'
    out.mkdir(parents=True)
    stage = args.stage.resolve()
    build = json.loads((stage / 'build.json').read_text())
    exe = stage / 'bin/dbaa_game.exe'
    assert build['executable_sha256'] == sha(exe)
    assert build['clean_source_build'] and not build['native_cpu_core_linked']
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / name) == digest for name, digest in build[field].items()), field
    validation = json.loads(args.validation.read_text())
    assert validation['executable_sha256'] == sha(exe) and validation['correctness_gates_passed']
    assert not validation['whole_game_validated']
    mgba = ROOT / 'tools/local/mgba_reference'
    assert subprocess.check_output(['git', '-C', str(mgba), 'rev-parse', 'HEAD'], text=True).strip() == MGBA_PIN
    package = out / ('DBAA-Windows-x64-' + args.version)
    package.mkdir()
    shutil.copyfile(exe, package / 'dbaa_game.exe')
    for p in (ROOT / 'port/windows/preview').iterdir():
        if p.is_file():
            shutil.copyfile(p, package / p.name)
    shutil.copyfile(ROOT / 'THIRD_PARTY_NOTICES.md', package / 'THIRD_PARTY_NOTICES.md')
    for name in ['docs/windows_preview.md', 'docs/zelda_base_assessment.md']:
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    third = package / 'third_party'
    third.mkdir()
    for name in ['gbarecomp-MIT.txt', 'mgba-MPL-2.0.txt', 'zelda-GPL-3.0.txt']:
        shutil.copyfile(ROOT / 'port/third_party' / name, third / name)
    # Exact corresponding MPL sources/headers, including the BIOS polynomial.
    # No mGBA executable, test ROM, BIOS image or commercial game data is copied.
    covered = [mgba / 'src' / name for name in ['gb/audio.c', 'core/timing.c', 'core/sync.c',
               'util/audio-buffer.c', 'util/circle-buffer.c', 'gba/bios.c']]
    covered += list((mgba / 'include').rglob('*.h'))
    for source in sorted(set(covered)):
        target = third / 'mgba-source' / source.relative_to(mgba)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    own_mpl = third / 'project-source'
    for name in ['port/include/bios_math.h', 'port/third_party/mgba/flags.h', 'port/audio/psg_mgba.c']:
        target = own_mpl / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (third / 'SOURCE.txt').write_text(
        'mGBA corresponding source revision: ' + MGBA_PIN + '\n'
        'https://github.com/mgba-emu/mgba/tree/' + MGBA_PIN + '\n'
        'The included original source files are unmodified. Project adapters and\n'
        'configuration are in project-source and the public repository.\n'
        'Complete build scripts and translator patch: ' + PROJECT + '\n', encoding='utf-8')
    # Exclude data accidentally copied by any future packaging change.
    forbidden = {'.gba', '.gb', '.gbc', '.bios', '.sav', '.eep', '.pcm', '.wav', '.bmp'}
    assert not [p for p in package.rglob('*') if p.is_file() and p.suffix.lower() in forbidden]
    dlls = subprocess.check_output([str(ROOT / 'tools/local/w64devkit/bin/objdump.exe'), '-p', str(exe)], text=True)
    imports = [line.split(':', 1)[1].strip() for line in dlls.splitlines() if 'DLL Name:' in line]
    assert not any(x.lower().startswith(('libgcc', 'libstdc++', 'sdl')) for x in imports), imports
    manifest = dict(version=args.version, platform='Windows x64', executable_sha256=sha(exe),
                    rom_required=True, rom_included=False, bios_included=False, game_assets_included=False,
                    rom_sha1='1338584d8cfa57402603197e65d2e2ff0184d24f',
                    native_cpu_interpreter_linked=False, whole_game_validated=False,
                    build_report_sha256=sha(stage / 'build.json'), validation=validation,
                    source_repository=PROJECT, mgba_commit=MGBA_PIN, system_dlls=imports,
                    files_sha256={p.relative_to(package).as_posix(): sha(p) for p in sorted(package.rglob('*')) if p.is_file()})
    (package / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (package / 'SHA256SUMS.txt').write_text(''.join(
        sha(p) + '  ' + p.relative_to(package).as_posix() + '\n'
        for p in sorted(package.rglob('*')) if p.is_file()), encoding='utf-8')
    archive = out / (package.name + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(package.rglob('*')):
            if p.is_file():
                z.write(p, package.name + '/' + p.relative_to(package).as_posix())
    (out / 'SHA256SUMS.txt').write_text(sha(archive) + '  ' + archive.name + '\n', encoding='utf-8')
    print(json.dumps(dict(archive=str(archive), bytes=archive.stat().st_size, sha256=sha(archive)), indent=2))


if __name__ == '__main__':
    main()
