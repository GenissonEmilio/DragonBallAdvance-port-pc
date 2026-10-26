"""Recreate bounded translation hints from the local USA ROM, never code proof."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

ROOT = Path(__file__).resolve().parents[1]
ROM_SHA1 = '1338584d8cfa57402603197e65d2e2ff0184d24f'
CODE_END = 0x0811855C


def discover(rom, header):
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = True
    h = lambda p: struct.unpack_from('<H', rom, p)[0]
    w = lambda p: struct.unpack_from('<I', rom, p)[0]
    known = {int(n, 16) for n in re.findall(r'void func_([0-9A-F]+)\(void\)', header)}
    pointers = sorted({value for (value,) in struct.iter_unpack('<I', rom)
                       if value & 1 and 0x080000C0 <= (value & ~1) < CODE_END
                       and (value & ~1) not in known})
    tables = []
    for pos in range(0xC0, CODE_END - 0x08000000, 2):
        raw = h(pos)
        if (raw & 0xFF87) != 0x4687:
            continue
        rx, ldpos = (raw >> 3) & 15, None
        for distance in range(2, 14, 2):
            prev, raw = pos - distance, h(pos - distance)
            if (raw & 0xF800) == 0x6800 and raw & 7 == rx and (raw >> 3) & 7 == rx and (raw >> 6) & 31 == 0:
                ldpos = prev
                break
            decoded = list(md.disasm(rom[prev:prev + 2], 0x08000000 + prev, count=1))
            if not decoded:
                break
            _, writes = decoded[0].regs_access()
            if 'r' + str(rx) in [md.reg_name(r) for r in writes] or decoded[0].mnemonic.startswith('b'):
                break
        if ldpos is None:
            continue
        add = h(ldpos - 2)
        if (add & 0xFE00) != 0x1800 or (add & 7) != rx:
            continue
        rs, rm, table, index = (add >> 3) & 7, (add >> 6) & 7, 0, None
        for p in range(ldpos - 4, max(0xC0, ldpos - 22), -2):
            raw = h(p)
            if (raw & 0xF800) == 0x4800 and ((raw >> 8) & 7) in [rs, rm]:
                table = w(((p + 0x08000004) & ~3) + ((raw & 255) * 4) - 0x08000000)
                index = rm if ((raw >> 8) & 7) == rs else rs
                break
        if not 0x080000C0 <= table < CODE_END or table & 3:
            continue
        count = 0
        for p in range(ldpos - 4, max(0xC0, ldpos - 50), -2):
            raw = h(p)
            if (raw & 0xF800) == 0 and ((raw >> 6) & 31) == 2 and (raw & 7) == index:
                index = (raw >> 3) & 7
            if (raw & 0xF800) == 0x2800 and ((raw >> 8) & 7) == index and (h(p + 2) & 0xFF00) in [0xD800, 0xD900]:
                count = (raw & 255) + 1
                break
        if not count or table - 0x08000000 + 4*count > len(rom):
            continue
        targets = [w(table - 0x08000000 + 4*i) for i in range(count)]
        if not all(0x080000C0 <= t < CODE_END for t in targets):
            continue
        tables.append(dict(branch=hex(0x08000000 + pos), table=hex(table), count=count,
                           targets=[hex(t | 1) for t in targets]))
    missing = sorted({int(t, 16) for table in tables for t in table['targets']
                      if (int(t, 16) & ~1) not in known})
    return pointers, missing, tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT / 'baserom.gba')
    parser.add_argument('--base-header', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    assert len(rom) == 0x1000000 and hashlib.sha1(rom).hexdigest() == ROM_SHA1
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pointers, missing, tables = discover(rom, args.base_header.read_text())
    combined = sorted(set(pointers) | set(missing))
    (out / 'extra_entries.txt').write_text(''.join(f'0x{a:08X}\n' for a in combined))
    (out / 'pointer_entries.txt').write_text(''.join(f'0x{a:08X}\n' for a in pointers))
    result = dict(rom_sha1=ROM_SHA1, code_end_hint=hex(CODE_END), hints_are_verified_code=False,
                  pointer_candidates=len(pointers), jump_table_candidates=len(missing), tables=len(tables),
                  combined_candidates=len(combined), gba_byte_matching=False, table_details=tables,
                  header_sha256=hashlib.sha256(args.base_header.read_bytes()).hexdigest(),
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out / 'discovery.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Discovered translation hints:', len(pointers), 'pointers,', len(missing), 'table entries;', len(combined), 'combined')


if __name__ == '__main__':
    main()
