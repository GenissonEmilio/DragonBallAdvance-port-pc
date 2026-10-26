"""Compare emitted shifter/data-processing results and NZCV to ROM instructions.

Samples come from local ROM bytes, including bytes outside the code hint.
This is isolated instruction
semantics, not proof that each sampled address is reachable game code or that
the full ISA/timing is implemented. PC operands and exception returns are excluded.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
import subprocess
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from capstone.arm import (ARM_REG_PC, ARM_INS_AND, ARM_INS_EOR, ARM_INS_TST, ARM_INS_TEQ,
                         ARM_INS_ORR, ARM_INS_MOV, ARM_INS_BIC, ARM_INS_MVN, ARM_INS_LSL,
                         ARM_INS_LSR, ARM_INS_ASR, ARM_INS_ROR, ARM_INS_RRX, ARM_INS_SUB,
                         ARM_INS_RSB, ARM_INS_ADD, ARM_INS_ADC, ARM_INS_SBC, ARM_INS_RSC,
                         ARM_INS_CMP, ARM_INS_CMN)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import (UC_CPU_ARM_926, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                              UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
                              UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10,
                              UC_ARM_REG_R11, UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR,
                              UC_ARM_REG_CPSR)

ROOT = Path(__file__).resolve().parents[1]
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
        UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
        UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR]
VALUES = [0, 1, 0x80, 0x4000, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFF]
AMOUNTS = [0, 1, 2, 7, 16, 31, 32, 33, 63, 64, 127, 128, 255, 256, 257, 0xFFFFFFFF]


def select(rom):
    chosen = {}
    # Fill the immediate/alias matrix from ROM bytes, extending past the code
    # hint when an encoding is absent there. These are instruction semantics
    # probes; the report deliberately makes no game-reachability claim.
    for offset in range(0xC0, len(rom), 2):
        raw = struct.unpack_from('<H', rom, offset)[0]
        if raw < 0x1800:
            kind, amount, rd, rs = raw >> 11, (raw >> 6) & 31, raw & 7, (raw >> 3) & 7
            key = ('T', 'immediate', kind, amount, rd == rs)
            chosen.setdefault(key, dict(mode='T', address=0x08000000 + offset, raw=raw, rd=rd, rs=rs,
                                        category='thumb_immediate', shift=kind, amount=amount))
        elif raw & 0xFC00 == 0x4000 and (raw >> 6) & 15 in [2, 3, 4, 7]:
            op, rd, rs = (raw >> 6) & 15, raw & 7, (raw >> 3) & 7
            key = ('T', 'register', op, rd == rs)
            chosen.setdefault(key, dict(mode='T', address=0x08000000 + offset, raw=raw, rd=rd, rs=rs,
                                        category='thumb_register', shift=op))
        if len(chosen) == 200:
            break
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    allowed = {ARM_INS_AND, ARM_INS_EOR, ARM_INS_TST, ARM_INS_TEQ, ARM_INS_ORR, ARM_INS_MOV,
               ARM_INS_BIC, ARM_INS_MVN, ARM_INS_LSL, ARM_INS_LSR, ARM_INS_ASR, ARM_INS_ROR,
               ARM_INS_RRX, ARM_INS_SUB, ARM_INS_RSB, ARM_INS_ADD, ARM_INS_ADC, ARM_INS_SBC,
               ARM_INS_RSC, ARM_INS_CMP, ARM_INS_CMN}
    # Limit categories, not result comparisons. Each selected instruction is
    # compared across every NZCV input; conditional execution is tested too.
    for offset in range(0xC0, 0x11855C, 4):
        raw = struct.unpack_from('<I', rom, offset)[0]
        op, flags, immediate = (raw >> 21) & 15, bool(raw & (1 << 20)), bool(raw & (1 << 25))
        # ARMv4 TST/TEQ/CMP/CMN require S=1. S=0 encodings include later
        # architecture MOVW/MOVT aliases that Capstone also calls MOV.
        if op in [8, 9, 10, 11] and not flags:
            continue
        if raw >> 28 == 15 or raw & 0x0C000000 or (not immediate and raw & 0x90 == 0x90):
            continue
        rd, rn, rm, rs = (raw >> 12) & 15, (raw >> 16) & 15, raw & 15, (raw >> 8) & 15
        # Keep reserved/unused ARMv4 operand fields zero. Random ROM data
        # also decodes to TEQ Rd!=0 or MOV Rn!=0; those are not valid probes.
        if op in [8, 9, 10, 11] and rd != 0 or op in [13, 15] and rn != 0:
            continue
        register = not immediate and bool(raw & 16)
        shift = (raw >> 5) & 3
        zero = not (raw & (0xF00 if immediate else 0xF80))
        key = ('A', op, flags, immediate, register, shift if not immediate else 0, zero)
        if key in chosen:
            continue
        decoded = list(md.disasm(rom[offset:offset + 4], 0x08000000 + offset, count=1))
        if not decoded or decoded[0].id not in allowed:
            continue
        reads, writes = decoded[0].regs_access()
        if ARM_REG_PC in reads or ARM_REG_PC in writes or rd == 15:
            continue
        if not immediate and (rm == 15 or register and rs == 15):
            continue
        chosen[key] = dict(mode='A', address=0x08000000 + offset, raw=raw, rd=rd, rn=rn, rm=rm, rs=rs,
                           category='arm_data_processing', opcode=op, set_flags=flags,
                           immediate=immediate, register=register, shift=shift)
    result = list(chosen.values())
    assert len([x for x in result if x['category'] == 'thumb_immediate']) == 192
    assert len([x for x in result if x['category'] == 'thumb_register']) == 8
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, default=ROOT / 'tools/local/sp00nz_gbarecomp')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_static_shift_validation')
    parser.add_argument('--expect-failure', action='store_true')
    parser.add_argument('--thumb-only', action='store_true', help='isolate the old Thumb carry regression')
    args = parser.parse_args()
    out, upstream = args.out_dir.resolve(), args.upstream.resolve()
    assert not out.exists(), 'preserve previous evidence'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rom_path = ROOT / 'baserom.gba'
    rom = rom_path.read_bytes()
    assert hashlib.sha1(rom).hexdigest() == '1338584d8cfa57402603197e65d2e2ff0184d24f'
    samples = select(rom)
    if args.thumb_only:
        samples = [s for s in samples if s['mode'] == 'T']
    (out / 'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    (out / 'emitter_snapshot.c').write_bytes((ROOT / 'tools/native_shift_emit.c').read_bytes())
    (out / 'samples.json').write_text(json.dumps(samples, indent=2) + '\n')
    (out / 'instructions.txt').write_text(''.join(f"{s['mode']} {s['address']:08x}\n" for s in samples))
    gcc = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    names = ['rom', 'arm', 'thumb', 'disasm', 'analysis', 'translate']
    sources = [upstream / 'src' / (n + '.c') for n in names]
    commands = [[str(gcc), '-std=c11', '-O2', '-I' + str(upstream / 'include'),
                 str(ROOT / 'tools/native_shift_emit.c'), *map(str, sources), '-o', str(out / 'emit.exe')],
                [str(out / 'emit.exe'), str(rom_path), str(out / 'instructions.txt'), str(out / 'probe.c')],
                [str(gcc), '-std=c11', '-O2', '-shared', '-Wall', '-Wextra', '-Werror',
                 '-I' + str(upstream / 'include'), str(out / 'probe.c'), '-o', str(out / 'probe.dll')]]
    for i, command in enumerate(commands):
        r = subprocess.run(command, capture_output=True, text=True)
        (out / f'build_{i}.log').write_text(json.dumps(command) + '\n' + r.stdout + r.stderr)
        assert r.returncode == 0, r.stderr[-4000:]
    dll = C.CDLL(str(out / 'probe.dll'))
    dll.Probe.argtypes = [C.c_uint, C.POINTER(C.c_uint32), C.c_uint32, C.POINTER(C.c_uint32)]
    dll.Probe.restype = C.c_int
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    uc.ctl_set_cpu_model(UC_CPU_ARM_926)
    uc.mem_map(0x08000000, len(rom))
    uc.mem_write(0x08000000, rom)
    digest = hashlib.sha256()
    counts, failures, total = {}, [], 0
    rng = random.Random(0x5A1F7)
    base = [rng.getrandbits(32) for _ in range(16)]
    for index, sample in enumerate(samples):
        amounts = AMOUNTS if sample.get('register') or sample['category'] == 'thumb_register' else [0]
        for value in VALUES:
            for amount in amounts:
                registers = list(base)
                if sample['mode'] == 'T':
                    registers[sample['rs']] = value if sample['category'] == 'thumb_immediate' else amount
                    if sample['category'] == 'thumb_register': registers[sample['rd']] = value
                else:
                    registers[sample['rn']] = value ^ 0x80000001
                    if not sample['immediate']: registers[sample['rm']] = value
                    if sample['register']: registers[sample['rs']] = amount
                for bits in range(16):
                    flags = bits << 28
                    uc.reg_write(UC_ARM_REG_CPSR, flags | (0x3F if sample['mode'] == 'T' else 0x1F))
                    for reg, val in zip(REGS, registers): uc.reg_write(reg, val)
                    address = sample['address']
                    width = 2 if sample['mode'] == 'T' else 4
                    uc.emu_start(address | (sample['mode'] == 'T'), address + width, count=1)
                    expected = [uc.reg_read(reg) for reg in REGS] + [uc.reg_read(UC_ARM_REG_CPSR) & 0xF0000000]
                    incoming = (C.c_uint32 * 16)(*registers)
                    actual = (C.c_uint32 * 16)()
                    assert dll.Probe(index, incoming, flags, actual)
                    result = list(actual)
                    if result != expected:
                        if len(failures) < 32:
                            failures.append(dict(sample=sample, value=value, amount=amount, flags=flags,
                                                 registers=registers, expected=expected, actual=result))
                        counts['mismatches'] = counts.get('mismatches', 0) + 1
                    digest.update(struct.pack('<16I', *result))
                    total += 1
                    counts[sample['category']] = counts.get(sample['category'], 0) + 1
        if index % 100 == 0: print('Compared instructions', index + 1, '/', len(samples), '; cases', total, flush=True)
    report = dict(samples=len(samples), cases=total, categories=counts, mismatches=counts.get('mismatches', 0),
                  first_failures=failures, results_sha256=digest.hexdigest(), nzcv_and_registers_equal=not failures,
                  rom_sha1=hashlib.sha1(rom).hexdigest(), compiler_sha256=sha(gcc), tool_sha256=sha(__file__),
                  emitter_sha256=sha(ROOT / 'tools/native_shift_emit.c'), probe_source_sha256=sha(out / 'probe.c'),
                  translator_sources_sha256={str(p): sha(p) for p in sources},
                  runtime_header_sha256=sha(upstream / 'include/gba/gba_runtime.h'),
                  thumb_only=args.thumb_only,
                  original_rom_instruction_bytes_used=True, game_reachability_claimed=False,
                  full_isa_validated=False, cpu_cycles_compared=False, native_cpu_interpreter_linked=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    assert bool(failures) == args.expect_failure, (counts, failures[:1])
    print('PASS' if not failures else 'EXPECTED OLD TRANSLATOR FAILURE', total, 'cases;', report['mismatches'], 'mismatches')


if __name__ == '__main__':
    main()
