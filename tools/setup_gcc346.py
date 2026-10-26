#!/usr/bin/env python3
"""Build the alternative GCC 3.4.6 matching compiler on Windows, out of tree.

Requires tools/setup_matching.ps1 and Git for Windows (its Bash). No compiler
source is patched. Only generated libiberty host-capability headers are adjusted
for modern MinGW's sys_errlist/sys_nerr macros.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HOST_FLAGS = ("-O2 -std=gnu89 -fcommon -fno-strict-aliasing -fwrapv "
              "-D__USE_MINGW_ANSI_STDIO=1 -Wno-implicit-function-declaration "
              "-Wno-implicit-int -Wno-error=incompatible-pointer-types")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(archive: Path, local: Path) -> int:
    """Compare every regular release file with its extracted source, byte for byte."""
    count = 0
    with tarfile.open(archive, "r:bz2") as release:
        for member in release:
            if member.isfile():
                expected = release.extractfile(member).read()
                path = local / member.name
                if not path.is_file() or path.read_bytes() != expected:
                    raise ValueError(f"release source differs: {path}")
                count += 1
    return count


def find_bash(explicit: Path | None) -> str:
    paths = [explicit] if explicit else [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe",
        Path(os.environ.get("LOCALAPPDATA", "C:/")) / "Programs/Git/bin/bash.exe",
    ]
    for path in paths:
        if path and path.is_file():
            # Old make recipes do not consistently quote SHELL; a short path
            # also handles the usual C:/Program Files/Git installation.
            buffer = ctypes.create_unicode_buffer(32768)
            if not ctypes.windll.kernel32.GetShortPathNameW(str(path.resolve()), buffer, len(buffer)):
                raise ValueError(f"cannot obtain Bash short path: {path}")
            result = buffer.value.replace("\\", "/")
            if " " in result:
                raise ValueError("Git Bash needs a path without spaces (or Windows short-path support)")
            return result
    raise ValueError("Git Bash not found; pass --bash PATH/TO/Git/bin/bash.exe")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify existing files without building or downloading")
    parser.add_argument("--bash", type=Path)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "tools/local/gcc346-build")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    try:
        if os.name != "nt":
            raise ValueError("this setup recipe targets Windows with w64devkit and Git Bash")
        if args.jobs < 1:
            raise ValueError("--jobs must be positive")
        config = json.loads((ROOT / "config/matching.json").read_text(encoding="utf-8"))
        profile = config["compiler_profiles"]["gcc346"]
        local = ROOT / "tools/local"
        archive = local / "gcc-core-3.4.6.tar.bz2"
        source = local / "gcc-3.4.6"
        build = args.build_dir.resolve()
        compiler = build / "gcc/cc1.exe"
        if build == source or source in build.parents:
            raise ValueError("compiler build must be outside the release source directory")
        local.mkdir(parents=True, exist_ok=True)
        if not archive.is_file():
            if args.check:
                raise ValueError(f"missing {archive}")
            partial = archive.with_suffix(archive.suffix + ".download")
            urllib.request.urlretrieve(profile["source_url"], partial)
            if sha256(partial) != profile["archive_sha256"]:
                raise ValueError("GCC release archive SHA-256 mismatch")
            partial.replace(archive)
        if sha256(archive) != profile["archive_sha256"]:
            raise ValueError("GCC release archive SHA-256 mismatch")
        if not source.is_dir():
            if args.check:
                raise ValueError(f"missing {source}")
            with tarfile.open(archive, "r:bz2") as release:
                # Python's data filter rejects paths/links escaping this tree.
                release.extractall(local, filter="data")
        files = verify_source(archive, local)
        print(f"Release source verified: {files} unchanged files.", flush=True)
        if not compiler.is_file():
            if args.check:
                raise ValueError(f"missing {compiler}")
            bash = find_bash(args.bash)
            host = ROOT / config["host_tools"]["directory"]
            for name in ("make.exe", "i686-w64-mingw32-gcc.exe", "ar.exe", "ranlib.exe"):
                if not (host / name).is_file():
                    raise ValueError(f"missing {host / name}; run tools/setup_matching.ps1 first")
            env = os.environ.copy()
            env.update(PATH=str(host) + os.pathsep + env.get("PATH", ""),
                       CONFIG_SHELL=bash, CC="i686-w64-mingw32-gcc", CFLAGS=HOST_FLAGS,
                       PWDCMD="pwd -W", INSTALL=(source / "install-sh").as_posix() + " -c")
            build.mkdir(parents=True, exist_ok=True)
            log_path = build / "setup.log"
            print(f"Building cc1; log: {log_path}", flush=True)
            with log_path.open("w", encoding="utf-8") as log:
                def run(command: list[str]) -> None:
                    log.write(json.dumps(command) + "\n")
                    log.flush()
                    result = subprocess.run(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
                    if result.returncode:
                        raise ValueError(f"build failed ({result.returncode}); see {log_path}")

                # The 2006 config.status splits drive-letter source paths at
                # ':'; keep configure/srcdir relative. PWDCMD retains native
                # Windows paths in Make dependencies instead of MSYS /c/ paths.
                configure = os.path.relpath(source / "configure", build).replace("\\", "/")
                run([bash, configure,
                     "--build=i686-pc-mingw32", "--host=i686-pc-mingw32", "--target=arm-elf",
                     "--disable-nls", "--disable-multilib", "--disable-shared", "--enable-languages=c",
                     "--without-headers", "--disable-checking"])
                make = [str(host / "make.exe"), f"-j{args.jobs}", f"SHELL={bash}",
                        "AR=ar.exe", "AR_FOR_BUILD=ar.exe", "RANLIB=ranlib.exe", "RANLIB_FOR_BUILD=ranlib.exe",
                        "CFLAGS=" + HOST_FLAGS, "CFLAGS_FOR_BUILD=" + HOST_FLAGS]
                run([*make, "configure-build-libiberty", "configure-libiberty"])
                for relative in ("libiberty/config.h", "build-i686-pc-mingw32/libiberty/config.h"):
                    header = build / relative
                    text = header.read_text(encoding="utf-8")
                    for macro in ("HAVE_SYS_ERRLIST", "HAVE_SYS_NERR"):
                        text = text.replace(f"#define {macro} 1", f"/* #undef {macro} */")
                    header.write_text(text, encoding="utf-8")
                run([*make, "all-build-libiberty", "all-libiberty", "configure-gcc"])
                # Preserve GCC's default BUILD_CFLAGS: it adds IN_GCC and
                # GENERATOR_FILE. ANSI stdio enables the generator's printf %n.
                run([*make, "-C", "gcc", "cc1.exe"])
            files = verify_source(archive, local)
        identity = subprocess.run([str(compiler), "--version"], capture_output=True, text=True, check=True)
        if "3.4.6" not in identity.stdout + identity.stderr:
            raise ValueError("unexpected compiler version")
        print(f"GCC 3.4.6 ready: {compiler}\nSHA-256: {sha256(compiler)}", flush=True)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
