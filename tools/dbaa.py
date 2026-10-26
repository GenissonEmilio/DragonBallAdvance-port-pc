#!/usr/bin/env python3
"""ROM identification, explicit ARM/Thumb listings and exact binary comparison.

This is analysis infrastructure, not a game port or an automatic decompiler.
No instruction masks or relocation exemptions are used by the comparator.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
ROM_BASE = 0x08000000
MAX_ROM_SIZE = 32 * 1024 * 1024
HEADER_SIZE = 0xC0
MEMORY = {
    "ewram": {"base": "0x02000000", "size": "0x40000"},
    "iwram": {"base": "0x03000000", "size": "0x8000"},
    "io": {"base": "0x04000000", "size": "0x400"},
    "palette": {"base": "0x05000000", "size": "0x400"},
    "vram": {"base": "0x06000000", "size": "0x18000"},
    "oam": {"base": "0x07000000", "size": "0x400"},
    "rom": {"base": "0x08000000", "maximum_size": "0x2000000"},
}


def number(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use decimal or hexadecimal (0x...)") from exc


def load_rom(path: Path) -> bytes:
    size = path.stat().st_size
    if not HEADER_SIZE <= size <= MAX_ROM_SIZE:
        raise ValueError("ROM must have 192 bytes to 32 MiB; extract ZIP files first")
    return path.read_bytes()


def header_checksum(data: bytes) -> int:
    if len(data) < HEADER_SIZE:
        raise ValueError("truncated GBA header")
    return (-sum(data[0xA0:0xBD]) - 0x19) & 0xFF


def reset_branch(data: bytes) -> int | None:
    """Decode only an unconditional ARM B at the cartridge entry, not arbitrary code."""
    if len(data) < 4:
        return None
    word = struct.unpack_from("<I", data)[0]
    if word & 0xFF000000 != 0xEA000000:
        return None
    relative = word & 0xFFFFFF
    if relative & 0x800000:
        relative -= 0x1000000
    return ROM_BASE + 8 + (relative << 2)


def inspect_rom(data: bytes, profiles: list[dict]) -> dict:
    if len(data) < HEADER_SIZE:
        raise ValueError("truncated GBA header")
    sha1 = hashlib.sha1(data).hexdigest()
    code = data[0xAC:0xB0].decode("ascii", errors="replace")
    match = next((p for p in profiles if p["sha1"] == sha1), None)
    checksum = header_checksum(data)
    target = reset_branch(data)
    markers = []
    pattern = rb"(?:EEPROM_V|SRAM_F_V|SRAM_V|FLASH1M_V|FLASH512_V|FLASH_V)\d{3}"
    for hit in re.finditer(pattern, data):
        markers.append({"name": hit.group().decode("ascii"), "offset": f"0x{hit.start():08X}"})
    valid = checksum == data[0xBD] and data[0xB2] == 0x96
    return {
        "size": len(data),
        "sha1": sha1,
        "sha256": hashlib.sha256(data).hexdigest(),
        "crc32": f"{zlib.crc32(data):08X}",
        "title": data[0xA0:0xAC].decode("ascii", errors="replace").rstrip("\x00 "),
        "game_code": code,
        "revision": data[0xBC],
        "header": {
            "fixed_byte_valid": data[0xB2] == 0x96,
            "checksum_stored": f"0x{data[0xBD]:02X}",
            "checksum_calculated": f"0x{checksum:02X}",
            "valid": valid,
        },
        "known_profile": match,
        "profile_header_consistent": match is not None and match["game_code"] == code,
        "reset_branch": f"0x{target:08X}" if target is not None else None,
        "reset_target_in_rom": target is not None and ROM_BASE <= target < ROM_BASE + len(data),
        "save_driver_markers": markers,
        "memory_map": MEMORY,
        "compiler": "unidentified; do not assume agbcc or any compiler from the platform alone",
        "notes": [
            "Header and driver markers identify leads, not function boundaries or proven save behavior.",
            "Profiles identify ROM hashes only; they do not provide version-specific address maps.",
        ],
    }


def region(data: bytes, start: int, size: int) -> tuple[int, bytes]:
    offset = start - ROM_BASE if start >= ROM_BASE else start
    if offset < 0 or size <= 0 or offset + size > len(data):
        raise ValueError("range must be positive and entirely inside the ROM")
    return offset, data[offset:offset + size]


def disassemble(data: bytes, address: int, mode: str) -> list[str]:
    try:
        import capstone
    except ImportError as exc:
        raise ValueError("install requirements.txt in the project virtual environment") from exc
    alignment = 4 if mode == "arm" else 2
    if address % alignment or len(data) % alignment:
        raise ValueError(f"{mode} start and size must be multiples of {alignment}")
    setting = capstone.CS_MODE_ARM if mode == "arm" else capstone.CS_MODE_THUMB
    decoder = capstone.Cs(capstone.CS_ARCH_ARM, setting | capstone.CS_MODE_LITTLE_ENDIAN)
    decoder.skipdata = True
    lines = [
        f"; linear {mode} listing, not proof that these bytes are ARMv4T instructions",
        "; identify literal pools, data and ARM/Thumb transitions before interpreting this listing",
    ]
    consumed = 0
    for insn in decoder.disasm(data, address):
        lines.append(f"{insn.address:08X}  {insn.bytes.hex(' '):<14} {insn.mnemonic:<9} {insn.op_str}".rstrip())
        consumed += insn.size
    if consumed != len(data):
        raise ValueError(f"decoder covered {consumed} of {len(data)} bytes")
    return lines


def compare_bytes(reference: bytes, candidate: bytes, limit: int = 16) -> dict:
    differences = []
    count = 0
    for offset in range(max(len(reference), len(candidate))):
        expected = reference[offset] if offset < len(reference) else None
        actual = candidate[offset] if offset < len(candidate) else None
        if expected != actual:
            count += 1
            if len(differences) < limit:
                differences.append({"offset": f"0x{offset:08X}", "reference": expected, "candidate": actual})
    return {
        "equal": count == 0,
        "reference_size": len(reference),
        "candidate_size": len(candidate),
        "different_bytes": count,
        "first_differences": differences,
        "reference_sha256": hashlib.sha256(reference).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "comparison": "exact bytes, including sizes; no relocation masking",
    }


def mapped_regions(data: bytes, mapping: dict) -> list[tuple[dict, int, bytes]]:
    if mapping.get("sha1") != hashlib.sha1(data).hexdigest():
        raise ValueError("address map does not match this ROM's SHA-1")
    result, names, spans = [], set(), []
    for entry in mapping.get("regions", []):
        name = entry.get("name", "")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in names:
            raise ValueError("map region names must be unique, lowercase identifiers")
        if entry.get("kind") not in ("arm", "thumb", "data"):
            raise ValueError(f"unknown region kind for {name}")
        start, size = int(entry["start"], 0), int(entry["size"], 0)
        offset, selected = region(data, start, size)
        if entry["kind"] != "data":
            alignment = 4 if entry["kind"] == "arm" else 2
            if offset % alignment or size % alignment:
                raise ValueError(f"unaligned code region: {name}")
        names.add(name)
        spans.append((offset, offset + size))
        result.append((entry, offset, selected))
    spans.sort()
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError("address map regions overlap")
    if not result:
        raise ValueError("address map has no regions")
    return result


def write_file(path: Path, data: bytes, protected: tuple[Path, ...] = ()) -> None:
    if any(path.resolve() == p.resolve() for p in protected):
        raise ValueError("output must not overwrite an input file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def emit_json(report: dict, out: Path | None, protected: tuple[Path, ...] = ()) -> None:
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if out is not None:
        write_file(out, text.encode("utf-8"), protected)
    print(text, end="")


def doctor() -> dict:
    try:
        version = importlib.metadata.version("capstone")
        import capstone
        capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        decoder = {"available": True, "version": version}
    except (ImportError, OSError, importlib.metadata.PackageNotFoundError) as exc:
        decoder = {"available": False, "error": str(exc)}
    matching_config = json.loads((ROOT / "config/matching.json").read_text(encoding="utf-8"))
    local_compiler = ROOT / matching_config["compiler"]["path"]
    return {
        "python": sys.version.split()[0],
        "capstone": decoder,
        "tools_on_path": {name: shutil.which(name) for name in (
            "arm-none-eabi-gcc", "arm-none-eabi-objdump", "arm-none-eabi-objcopy", "clang", "cmake", "mgba")},
        "matching_compiler": {
            "family": matching_config["compiler"]["family"],
            "available": local_compiler.is_file(),
            "path": str(local_compiler),
            "flags": matching_config["compiler"]["flags"],
            "check": "python tools/match.py; historical original executable not uniquely established",
        },
        "native_port": "not implemented",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="identify and validate a raw GBA ROM")
    inspect.add_argument("rom", type=Path)
    inspect.add_argument("--out", type=Path)
    inspect.add_argument("--require-known", action="store_true")
    split = commands.add_parser("split", help="extract reviewed ranges from a hash-bound address map")
    split.add_argument("rom", type=Path)
    split.add_argument("--map", type=Path, default=ROOT / "config/regions.usa.json")
    split.add_argument("--out-dir", type=Path, default=ROOT / "build/usa")
    for name in ("slice", "disasm"):
        command = commands.add_parser(name, help="extract an explicit ROM range" if name == "slice" else "list an explicit ARM/Thumb range")
        command.add_argument("rom", type=Path)
        command.add_argument("--start", required=True, type=number, help="file offset or primary ROM address (0x08000000...)")
        command.add_argument("--size", required=True, type=number)
        command.add_argument("--out", type=Path, required=name == "slice")
        if name == "disasm":
            command.add_argument("--mode", choices=("arm", "thumb"), required=True)
    compare = commands.add_parser("compare", help="compare raw binaries exactly (use linked, relocated code)")
    compare.add_argument("reference", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--out", type=Path)
    commands.add_parser("doctor", help="report analysis and compiler readiness")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            emit_json(doctor(), None)
            return 0
        if args.command == "compare":
            report = compare_bytes(args.reference.read_bytes(), args.candidate.read_bytes())
            emit_json(report, args.out, (args.reference, args.candidate))
            return 0 if report["equal"] else 1
        data = load_rom(args.rom)
        if args.command == "split":
            mapping = json.loads(args.map.read_text(encoding="utf-8"))
            ranges = mapped_regions(data, mapping)
            outputs, index = [], []
            for entry, offset, selected in ranges:
                outputs.append((args.out_dir / f"{entry['name']}.bin", selected))
                if entry["kind"] != "data":
                    listing = "\n".join(disassemble(selected, ROM_BASE + offset, entry["kind"])) + "\n"
                    outputs.append((args.out_dir / f"{entry['name']}.txt", listing.encode("utf-8")))
                index.append({**entry, "sha256": hashlib.sha256(selected).hexdigest()})
            protected = (args.rom, args.map)
            index_path = args.out_dir / "index.json"
            if any(path.resolve() in {p.resolve() for p in protected} for path, _ in outputs + [(index_path, b"")]):
                raise ValueError("split output must not overwrite an input file")
            for path, content in outputs:
                write_file(path, content, protected)
            emit_json({"rom_sha1": mapping["sha1"], "regions": index, "validation": "static analysis; no reconstructed C claimed"}, index_path, protected)
            return 0
        if args.command == "inspect":
            profiles = json.loads((ROOT / "config/roms.json").read_text(encoding="utf-8"))["profiles"]
            report = inspect_rom(data, profiles)
            emit_json(report, args.out, (args.rom,))
            accepted = report["header"]["valid"]
            if args.require_known:
                accepted = accepted and report["known_profile"] is not None and report["profile_header_consistent"]
            return 0 if accepted else 2
        offset, selected = region(data, args.start, args.size)
        if args.command == "slice":
            write_file(args.out, selected, (args.rom,))
            print(f"extracted {len(selected)} bytes at 0x{ROM_BASE + offset:08X} -> {args.out}")
        else:
            text = "\n".join(disassemble(selected, ROM_BASE + offset, args.mode)) + "\n"
            if args.out is not None:
                write_file(args.out, text.encode("utf-8"), (args.rom,))
            print(text, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
