#!/usr/bin/env python3
"""Assemble explicit GBA reconstructions; never count these as compiled C."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

import dbaa

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT/'baserom.gba')
    parser.add_argument('--target', default='music_player_update')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--out-dir', type=Path)
    args = parser.parse_args(argv)
    log = []
    def run(command):
        result = subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,text=True)
        log.append(json.dumps(list(map(str,command)))+'\n'+result.stdout+result.stderr)
        if result.returncode:
            raise ValueError(result.stderr.strip())
        return result.stdout
    try:
        config = json.loads((ROOT/'config/matching.json').read_text())
        manifest_path = ROOT/'config/assembly.usa.json'
        manifest = json.loads(manifest_path.read_text())
        symbols_path = ROOT/'config/symbols.usa.json'
        symbols = json.loads(symbols_path.read_text())
        if args.all:
            if args.source:
                raise ValueError('--source requires a single target')
            base=args.out_dir.resolve() if args.out_dir else ROOT/'build/assembly_matching'
            base.mkdir(parents=True,exist_ok=True)
            rows=[]
            for target in manifest['functions']:
                out=base/target['id']
                result=subprocess.run([sys.executable,__file__,'--rom',str(args.rom.resolve()),'--target',target['id'],'--out-dir',str(out)],cwd=ROOT)
                report_path=out/'report.json'
                rows.append(dict(id=target['id'],returncode=result.returncode,report=json.loads(report_path.read_text()) if result.returncode in (0,1) and report_path.exists() else None))
            (base/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(f'Assembly matching: {sum(r["returncode"]==0 for r in rows)}/{len(rows)}; excluded from C counts')
            return max(r['returncode']for r in rows)
        rom = dbaa.load_rom(args.rom)
        if hashlib.sha1(rom).hexdigest() != manifest['rom_sha1'] or manifest['rom_sha1'] != config['rom_sha1'] or symbols['rom_sha1'] != config['rom_sha1']:
            raise ValueError('requires the exact USA ROM SHA-1 and matching manifests')
        target = next((t for t in manifest['functions'] if t['id']==args.target),None)
        if target is None:
            raise ValueError('unknown assembly target')
        source = args.source.resolve() if args.source else ROOT/target['source']
        out = args.out_dir.resolve() if args.out_dir else ROOT/'build/assembly_matching'/args.target
        if out in {source.parent, args.rom.resolve().parent}:
            raise ValueError('outputs require a dedicated build directory')
        out.mkdir(parents=True,exist_ok=True)
        report_path=out/'report.json'
        report_path.unlink(missing_ok=True)
        address=int(target['address'],0)
        _, reference=dbaa.region(rom,address,target['size'])
        arm=ROOT/config['arm_tools']['directory']
        programs={name:arm/f'arm-none-eabi-{name}.exe' for name in ['as','ld','objcopy','objdump','readelf']}
        extern=out/'extern_symbols.s'
        excluded={target['name'],*target.get('internal_symbols',[])}
        extern.write_text('.thumb\n'+''.join(f'.global {name}\n.thumb_set {name}, {value}\n' for name,value in symbols['thumb_functions'].items() if name not in excluded))
        linker=out/'target.ld'
        definitions='\n'.join(f'{name} = {value};' for name,value in symbols['data'].items())
        linker.write_text('OUTPUT_FORMAT("elf32-littlearm")\nOUTPUT_ARCH(arm)\n'+f'ENTRY({target["name"]})\n'+definitions+f'\nSECTIONS {{ .text 0x{address:08X} : {{ *(.text) *(.text.*) }} /DISCARD/ : {{ *(.ARM.attributes) *(.comment) *(.note*) }} }}\n')
        obj,elf,binary=[out/f'{args.target}.{ext}' for ext in ['o','elf','bin']]
        flags=['-mcpu=arm7tdmi','-mthumb-interwork','-no-pad-sections']
        run([programs['as'],*flags,source,'-o',obj])
        run([programs['as'],'-mcpu=arm7tdmi',extern,'-o',out/'extern_symbols.o'])
        run([programs['ld'],'-T',linker,obj,out/'extern_symbols.o','-o',elf])
        relocs=run([programs['readelf'],'-rW',elf])
        if re.search(r'\bR_ARM_',relocs):
            raise ValueError('unresolved relocations')
        sections=run([programs['objdump'],'-h',elf])
        text=re.search(r'^\s*\d+\s+\.text\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)',sections,re.M)
        if not text or int(text.group(2),16)!=address:
            raise ValueError('wrong linked address')
        for section in re.finditer(r'^\s*\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+[^\n]*\n([^\n]*)',sections,re.M):
            name,size_hex,attrs=section.groups()
            if name!='.text' and int(size_hex,16) and 'ALLOC' in attrs:
                raise ValueError(f'uncompared allocated section: {name}')
        run([programs['objcopy'],'-O','binary','-j','.text',elf,binary])
        (out/f'{args.target}.disassembly.txt').write_text(run([programs['objdump'],'-d',elf]))
        (out/f'{args.target}.reference.bin').write_bytes(reference)
        report=dict(kind='assembly',counts_as_c=False,function=target['name'],rom_sha1=manifest['rom_sha1'],
            start=target['address'],end_exclusive=f'0x{address+target["size"]:08X}',
            instruction_bytes=target['instruction_bytes'],literal_bytes=target['literal_bytes'],padding_bytes=target['padding_bytes'],
            source_sha256=sha(source),assembly_manifest_sha256=sha(manifest_path),symbols_sha256=sha(symbols_path),
            tool_sha256=sha(__file__),matching_config_sha256=sha(ROOT/'config/matching.json'),
            assembler_path=str(programs['as'].relative_to(ROOT)),assembler_flags=flags,assembler_sha256=sha(programs['as']),
            assembler_version=run([programs['as'],'--version']).splitlines()[0],
            linker_sha256=sha(linker),external_symbols_sha256=sha(extern),
            assembly_postprocessing=False,remaining_relocations=False,
            **dbaa.compare_bytes(reference,binary.read_bytes()))
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        (out/'build.log').write_text('\n'.join(log))
        print(('MATCH' if report['equal'] else 'MISMATCH')+f' (ASSEMBLY): {target["name"]}: {report["candidate_size"]}/{report["reference_size"]} bytes, {report["different_bytes"]} differences')
        return 0 if report['equal'] else 1
    except (OSError,ValueError,KeyError) as error:
        print(f'error: {error}',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
