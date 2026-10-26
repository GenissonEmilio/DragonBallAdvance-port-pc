#!/usr/bin/env python3
"""Compile reconstructed C functions and compare every linked byte with the USA ROM."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import dbaa

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=ROOT / "baserom.gba")
    parser.add_argument("--source", type=Path, help="optional C candidate, for controlled experiments")
    parser.add_argument("--function-map", type=Path, default=ROOT / "config/functions.usa.json",
                        help="function manifest; use a separate build/ manifest for unverified candidates")
    parser.add_argument("--target", default="state_counter", help="function id from config/functions.usa.json")
    parser.add_argument("--all", action="store_true", help="rebuild and compare every configured function")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args(argv)
    log = []

    def run(command: list[str | Path]) -> str:
        command = [str(part) for part in command]
        log.append(json.dumps(command))
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        log.append(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError(f"{Path(command[0]).name} failed ({result.returncode}): {result.stderr.strip()}")
        return result.stdout

    try:
        config = json.loads((ROOT / "config/matching.json").read_text(encoding="utf-8"))
        functions = json.loads(args.function_map.read_text(encoding="utf-8"))
        symbols = json.loads((ROOT / "config/symbols.usa.json").read_text(encoding="utf-8"))
        if functions["rom_sha1"] != config["rom_sha1"] or symbols["rom_sha1"] != config["rom_sha1"]:
            raise ValueError("function and symbol maps must belong to the configured ROM")
        targets = {"state_counter": config["target"]}
        targets.update({entry["id"]: entry for entry in functions["functions"]})
        if args.all:
            if args.source:
                raise ValueError("--source requires a single target")
            base = args.out_dir.resolve() if args.out_dir else ROOT / "build/matching"
            results = []
            for target_id in targets:
                result = subprocess.run([sys.executable, __file__, "--rom", str(args.rom.resolve()),
                                         "--function-map", str(args.function_map.resolve()),
                                         "--target", target_id, "--out-dir", str(base / target_id)], cwd=ROOT)
                report_path = base / target_id / "report.json"
                results.append({"id": target_id, "returncode": result.returncode,
                                "report": json.loads(report_path.read_text())
                                if result.returncode in (0, 1) and report_path.exists() else None})
            base.mkdir(parents=True, exist_ok=True)
            (base / "summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
            passed = sum(row["returncode"] == 0 for row in results)
            print(f"Matching: {passed}/{len(results)} functions; {base / 'summary.json'}")
            return max(row["returncode"] for row in results)
        rom = dbaa.load_rom(args.rom)
        rom_sha1 = hashlib.sha1(rom).hexdigest()
        if rom_sha1 != config["rom_sha1"]:
            raise ValueError("this target requires the exact USA ROM SHA-1 in config/matching.json")
        if args.target not in targets:
            raise ValueError(f"unknown target {args.target}; choose from {', '.join(targets)}")
        target = targets[args.target]
        profile_id = target.get("compiler_profile", "agbcc")
        compiler_config = (config["compiler"] if profile_id == "agbcc"
                           else config.get("compiler_profiles", {}).get(profile_id))
        if not isinstance(compiler_config, dict):
            raise ValueError(f"unknown compiler profile: {profile_id}")
        compiler_flags = target.get("compiler_flags", compiler_config["flags"])
        label_metadata = target.get("label_metadata")
        address = int(target["address"], 0)
        size = target.get("size") or target["instruction_bytes"] + target["literal_bytes"]
        _, reference = dbaa.region(rom, address, size)
        source = args.source.resolve() if args.source else ROOT / target["source"]
        out = args.out_dir.resolve() if args.out_dir else ROOT / "build/matching" / args.target
        linker = ROOT / target["linker_script"] if "linker_script" in target else out / "target.ld"
        header = ROOT / "include/game_state.h"
        compiler = ROOT / compiler_config["path"]
        arm = ROOT / config["arm_tools"]["directory"]
        programs = {name: arm / f"arm-none-eabi-{name}.exe" for name in ("gcc", "as", "ld", "objcopy", "objdump", "readelf")}
        padding = ROOT / "config/gas_padding.s"
        required = [source, header, compiler, padding, *programs.values()]
        if "linker_script" in target:
            required.append(linker)
        for path in required:
            if not path.is_file():
                raise ValueError(f"missing {path}; see {compiler_config.get('setup', 'tools/setup_matching.ps1')}")

        paths = {extension: out / f"{args.target}.{extension}" for extension in ("i", "s", "o", "elf", "bin", "reference.bin", "disassembly.txt")}
        protected = {p.resolve() for p in (args.rom, source, linker, header, args.function_map,
                                          ROOT / "config/matching.json", ROOT / "config/symbols.usa.json")}
        if any(p.resolve() in protected for p in [*paths.values(), out / "report.json", out / "build.log"]):
            raise ValueError("build outputs cannot overwrite input files")
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").unlink(missing_ok=True)
        if "linker_script" not in target:
            definitions = "\n".join(f"{name} = {value};" for name, value in symbols["data"].items())
            metadata_output = ""
            if label_metadata:
                section = label_metadata["section"]
                if not re.fullmatch(r"\.debug_[a-zA-Z0-9_]+", section):
                    raise ValueError("label metadata requires a named debug section")
                # GNU C label addresses retain basic-block boundaries. They are
                # debugger metadata, never part of the ROM's executable image.
                metadata_output = f'{section} 0 (INFO) : {{ *({section}) }} '
            linker.write_text('OUTPUT_FORMAT("elf32-littlearm")\nOUTPUT_ARCH(arm)\n'
                              + f'ENTRY({target["name"]})\n' + definitions
                              + f'\nSECTIONS {{ .text 0x{address:08X} : {{ FILL(0); *(.text) *(.text.*) . = ALIGN(4); }} '
                              + metadata_output
                              + '/DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) } }\n', encoding="utf-8")
        external_asm = out / "extern_symbols.s"
        external_object = out / "extern_symbols.o"
        external_asm.write_text('.thumb\n' + ''.join(
            f'.global {name}\n.thumb_set {name}, {value}\n'
            for name, value in symbols["thumb_functions"].items() if name != target["name"]), encoding="utf-8")
        run([programs["as"], "-mcpu=arm7tdmi", external_asm, "-o", external_object])

        run([programs["gcc"], "-E", "-P", "-nostdinc", "-Iinclude", source, "-o", paths["i"]])
        run([compiler, *compiler_flags, paths["i"], "-o", paths["s"]])
        assembly = paths["s"].read_text(encoding="utf-8")
        version = re.search(compiler_config.get("assembly_version_regex",
                            r"Generated by gcc ([^\r\n]+)"), assembly, re.M)
        version_prefix = compiler_config.get("assembly_version_prefix", "2.9-arm-000512 ")
        if not version or not version.group(1).startswith(version_prefix):
            raise ValueError(f"unexpected compiler identity for profile {profile_id}")
        assembly_sha256 = digest(paths["s"])
        run([programs["as"], "-mcpu=arm7tdmi", "-mthumb-interwork", "-no-pad-sections", paths["s"], padding, "-o", paths["o"]])
        run([programs["ld"], "-T", linker, "-Map", out / f"{args.target}.map", paths["o"], external_object, "-o", paths["elf"]])
        relocation_report = run([programs["readelf"], "-rW", paths["elf"]])
        if re.search(r"\bR_ARM_", relocation_report):
            raise ValueError("linked candidate still contains ARM relocations")
        sections = run([programs["objdump"], "-h", paths["elf"]])
        text = re.search(r"^\s*\d+\s+\.text\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", sections, re.M)
        if not text or int(text.group(2), 16) != address:
            raise ValueError("candidate .text is not linked at the original ROM address")
        # Reject data or code that objcopy's .text-only extraction would hide.
        # Empty sections and non-allocated debugger metadata need no ROM bytes.
        for section in re.finditer(r"^\s*\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+[^\n]*\n([^\n]*)",
                                   sections, re.M):
            name, size_hex, flags = section.groups()
            if name != ".text" and int(size_hex, 16) and "ALLOC" in flags:
                raise ValueError(f"uncompared allocated section: {name}")
        metadata_report = None
        if label_metadata:
            section = label_metadata["section"]
            section_match = re.search(r"^\s*\d+\s+" + re.escape(section)
                                      + r"\s+([0-9a-fA-F]+)[^\n]*\n([^\n]*)", sections, re.M)
            if not section_match or "ALLOC" in section_match.group(2) or "CODE" in section_match.group(2):
                raise ValueError("label metadata must exist as non-allocated, non-executable debug information")
            metadata_size = int(section_match.group(1), 16)
            if metadata_size != 4 * label_metadata["entries"]:
                raise ValueError("unexpected label metadata size")
            metadata_report = {"section": section, "size": metadata_size,
                               "allocatable": False, "executable": False}
        run([programs["objcopy"], "-O", "binary", "-j", ".text", paths["elf"], paths["bin"]])
        disassembly = run([programs["objdump"], "-d", paths["elf"]])
        paths["disassembly.txt"].write_text(disassembly, encoding="utf-8")
        if digest(paths["s"]) != assembly_sha256:
            raise ValueError("compiler assembly was modified during the build")

        paths["reference.bin"].write_bytes(reference)
        candidate = paths["bin"].read_bytes()
        report = {
            "function": target["name"], "rom_sha1": rom_sha1,
            "start": f"0x{address:08X}", "end_exclusive": f"0x{address + size:08X}",
            "instruction_bytes": target.get("instruction_bytes"), "literal_bytes": target.get("literal_bytes"),
            "compiler": version.group(1), "compiler_flags": compiler_flags,
            "compiler_profile": profile_id,
            "compiler_path": compiler_config["path"],
            "compiler_source_commit": compiler_config.get("source_commit"),
            "compiler_source_archive_sha256": compiler_config.get("archive_sha256"),
            "compiler_executable_sha256": digest(compiler),
            "matching_config_sha256": digest(ROOT / "config/matching.json"),
            "matching_tool_sha256": digest(Path(__file__)),
            "source_sha256": digest(source), "header_sha256": digest(header), "linker_sha256": digest(linker),
            "function_manifest_sha256": digest(args.function_map),
            "compiler_barriers": target.get("compiler_barriers", []),
            "headers_sha256": {str(path.relative_to(ROOT)): digest(path) for path in sorted((ROOT / "include").rglob("*.h"))},
            "external_symbols_sha256": digest(external_asm),
            "section_padding": "explicit .balign 4,0 assembler suffix and zero linker alignment",
            "assembler_padding_sha256": digest(padding),
            "generated_assembly_sha256": assembly_sha256,
            "assembly_postprocessing": False, "remaining_relocations": False,
            **dbaa.compare_bytes(reference, candidate),
        }
        if metadata_report:
            report["label_metadata"] = metadata_report
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (out / "build.log").write_text("\n".join(log), encoding="utf-8")
        status = "MATCH" if report["equal"] else "MISMATCH"
        print(f"{status}: {target['name']} at 0x{address:08X}; {len(candidate)}/{len(reference)} bytes, {report['different_bytes']} differences")
        print(f"report: {out / 'report.json'}")
        return 0 if report["equal"] else 1
    except (OSError, ValueError, KeyError) as exc:
        if args.out_dir and args.out_dir.is_dir() and log:
            (args.out_dir / "build.log").write_text("\n".join(log), encoding="utf-8")
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
