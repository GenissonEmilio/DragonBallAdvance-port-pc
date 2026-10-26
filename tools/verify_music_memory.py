"""Validate MEMACC, XCMD, all 12 XCMD slots and GOTO against the USA ROM."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import random
import struct
import verify_music_player as v
import verify_music_end_tie as held
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB

ROOT=Path(__file__).resolve().parents[1]
MEMORY=v.E+0x18000
BRANCH=v.COMMANDS+0x80
MEMACC,XCMD,GOTO=0x0810BFAC,0x0810C104,0x0810A554
SLOTS=list(struct.unpack_from('<12I',v.ROM,0xA67708))
REGIONS=[(0x0810BFAC,0x0810BFDA),(0x0810C028,0x0810C0F2),(0x0810C0F8,0x0810C104),
         (0x0810C104,0x0810C11E),(0x0810C124,0x0810C132),(0x0810C138,0x0810C16E),
         (0x0810A554,0x0810A574),*( (a,a+(12 if a in [0x0810C1E4,0x0810C1F0]else 18))
         for a in [0x0810C180,0x0810C194,0x0810C1A8,0x0810C1BC,0x0810C1D0,0x0810C1E4,0x0810C1F0,0x0810C1FC,0x0810C210])]
DECODER=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
EXPECTED={i.address for a,b in REGIONS for i in DECODER.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}


def initial(seed):
    ew,iw=map(bytearray,v.fixture(seed%1000))
    ew[MEMORY-v.E:MEMORY-v.E+256]=bytes((i*17+seed)&255 for i in range(256))
    v.w32(ew,v.PLAYER-v.E+0x18,MEMORY)
    v.w32(ew,v.TRACKS-v.E+0x20,0)
    v.w32(ew,v.TRACKS-v.E+0x40,v.COMMANDS)
    v.w32(iw,0x1C70,0x0810A4E5);v.w32(iw,0x1C74,GOTO+1)
    return ew,iw


def config(target,seed,reads):
    return dict(address=target,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[target|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=GOTO,cover_end=0x0810C222,observe_reads=reads)


def memory_case(route,seed,op,left,right,alias=None,callback=None):
    ew,iw=initial(seed);base=MEMORY if alias is None else v.TRACKS+alias
    v.w32(ew,v.PLAYER-v.E+0x18,base)
    index,source=5,9
    ew[base-v.E+index]=left
    if op in [3,4,5]or op>=12:ew[base-v.E+source]=right
    data=source if op in [3,4,5]or 12<=op<=17 else right
    ew[v.COMMANDS-v.E:v.COMMANDS-v.E+3]=bytes([op,index,data])
    v.w32(ew,v.COMMANDS-v.E+3,BRANCH)
    if callback is not None:v.w32(iw,0x1C74,callback)
    reads=[v.TRACKS+0x40,v.PLAYER+0x18,base+index,base+source,0x03001C74,
           *range(v.COMMANDS,v.COMMANDS+7)]
    return route,seed,[ew,iw],config(MEMACC,seed,reads)


def extended_case(route,seed,index,parameter,alias=None):
    ew,iw=initial(seed)
    command=v.COMMANDS if alias is None else v.TRACKS+alias
    ew[command-v.E:command-v.E+5]=bytes([index,*parameter])
    v.w32(ew,v.TRACKS-v.E+0x40,command)
    reads=[v.TRACKS+0x40,*range(command,command+5),0x08A67708+4*index,0x03001C70]
    return route,seed,[ew,iw],config(XCMD,seed,reads)


def goto_case(seed,value,offset=None,low=False):
    ew,iw=initial(seed)
    command=v.COMMANDS if offset is None else v.TRACKS+offset
    extra=[]
    if low:
        command=0x01000000+seed%32
        extra=[(command,value.to_bytes(4,'little'))]
    else:v.w32(ew,command-v.E,value)
    v.w32(ew,v.TRACKS-v.E+0x40,command)
    cfg=config(GOTO,seed,[v.TRACKS+0x40,*range(command,command+4)])
    if extra:cfg['extra_memory']=extra
    return 'goto_filtered'if low else'goto',seed,[ew,iw],cfg


def variants(cases):
    edges=[0,1,127,128,254,255]
    for op in range(18):
        for seed in range(16):
            yield memory_case('memory_ops',op*16+seed,op,edges[seed%6],edges[(seed//2)%6])
    for op in range(6,18):
        for left in edges:
            for right in edges:
                yield memory_case('comparisons',op*256+left+right,op,left,right)
    for op in range(18,256):yield memory_case('invalid_ops',op,op,127,255)
    for index in range(12):
        for seed in range(16):
            parameter=[(seed*17)&255,128,254,255]
            yield extended_case('extended',index*16+seed,index,parameter)
    for seed in range(64):
        value=(0x81FE7F00+seed*0x01020304)&0xFFFFFFFF
        yield goto_case(seed,value)
        if seed<16:yield goto_case(seed,value,low=True)
    for op in range(18):
        for offset in [0x20,0x28,0x38,0x40]:
            yield memory_case('memory_aliases',op*4+offset,op,0xFF,1,offset)
    for index in range(12):
        for offset in [0x18,0x24,0x28,0x2C,0x3C,0x44]:
            yield extended_case('extended_aliases',index+offset,index,[1,2,3,4],offset)
    for seed,offset in enumerate([0,4,0x18,0x20,0x24,0x28,0x2C,0x3C,0x40,0x41,0x44,0x4C]):
        route,n,ram,cfg=goto_case(seed,0x89ABCDEF,offset)
        yield 'goto_aliases',n,ram,cfg
    # Replaced callbacks must still be consulted rather than bypassed.
    for seed in range(16):
        yield memory_case('callback_substitution',seed,6,60,60,callback=0x08010105)
    rng=random.Random(0xBFACC104)
    for seed in range(cases):
        if seed&1:
            yield extended_case('random',seed,rng.randrange(12),[rng.randrange(256)for _ in range(4)])
        else:yield memory_case('random',seed,rng.randrange(256),rng.randrange(256),rng.randrange(256))
    player_seed=0
    for route,seed,ram,cfg in held.variants(0):
        if route!='player_held_note':continue
        for variant in range(2):
            ew,iw=map(bytearray,ram);n=player_seed;player_seed+=1
            op=n%18 if n<120 else 18+(n-120)*29
            left=edges[n%6];right=edges[(n//6)%6]
            ew[MEMORY-v.E:MEMORY-v.E+256]=bytes(256)
            ew[MEMORY-v.E+5]=left;ew[MEMORY-v.E+9]=right
            v.w32(ew,v.PLAYER-v.E+0x18,MEMORY)
            v.w32(iw,v.TABLE-v.I+8*4,MEMACC+1);v.w32(iw,v.TABLE-v.I+28*4,XCMD+1)
            v.w32(iw,0x1C74,GOTO+1)
            data=9 if op in [3,4,5]or 12<=op<=17 else right
            prefix=[0xB9,op,5,data]
            if 6<=op<=17:prefix+=list(BRANCH.to_bytes(4,'little'))
            index=[1,2,4,5,6,7,8,9,10,11][n%10]
            parameter=list(v.WAVE.to_bytes(4,'little'))if index==1 else[0 if index==2 else right]
            for command,key in [(v.COMMANDS,60),(BRANCH,61)]:
                stream=([*prefix]if command==v.COMMANDS else[])+[0xCD,index,*parameter,0xCF,key,100,0x81,0xCE,key,0x81,0xB1]
                ew[command-v.E:command-v.E+len(stream)]=bytes(stream)
            taken=False
            if 6<=op<=17:
                rhs=right
                taken=[left==rhs,left!=rhs,left>rhs,left>=rhs,left<=rhs,left<rhs][(op-6)%6]
            yield 'player',n,[ew,iw],dict(cfg,cover_start=GOTO,cover_end=0x0810C222,
                expected_note=61 if taken else 60,require_goto=taken)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_memory_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires the configured USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();fallback=set();result=hashlib.sha256();players=0
    for index,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
            assert original==native,'RAM, resource reads or callback traces differ'
            if route=='player':
                assert {MEMACC,XCMD}<=v.COVERAGE,'real commands not reached'
                if cfg['require_goto']:assert GOTO in v.COVERAGE,'branch callback not reached'
                memory=original[0];head=v.u32(memory,v.TRACKS-v.E+0x20)
                offset=head-v.E if head<v.I else 0x40000+head-v.I
                assert head and memory[offset]&0xC0==0xC0
                assert memory[offset+0x11]==cfg['expected_note'] and memory[offset+0x10]==0
                players+=1
            assert not v.FALLBACK_TARGETS if route!='callback_substitution'else v.FALLBACK_TARGETS=={0x08010104}
            error=None
        except Exception as exc:error=repr(exc)
        if error:
            (v.OUT/'failed_case.json').write_text(json.dumps(dict(route=route,seed=seed,index=index,error=error),indent=2)+'\n')
            print('FAIL:',route,seed,error,flush=True);return 1
        counts[route]=counts.get(route,0)+1;coverage.update(v.COVERAGE&EXPECTED);fallback.update(v.FALLBACK_TARGETS)
        result.update(original[0])
        if index%256==0:print('Passed memory/XCMD cases:',index+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==264
    report=dict(cases=sum(counts.values()),routes=counts,rom_sha1=expected,random_cases=args.cases,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        operation_bytes_tested=256,extended_indices_tested=list(range(12)),extended_table_slots=SLOTS,
        real_player_cases=players,real_commands_reached=True,real_conditional_branches_verified=True,held_notes_verified=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=sorted(fallback),
        synthetic_callback_target=0x08010104,native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        shared_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_player.py').read_bytes()).hexdigest(),
        held_fixture_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_end_tie.py').read_bytes()).hexdigest(),
        native_dll_sha256=hashlib.sha256((v.OUT/'music_player_native.dll').read_bytes()).hexdigest(),
        compiler_sha256=hashlib.sha256(v.HOST_GCC.read_bytes()).hexdigest(),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=result.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'memory/XCMD cases;',len(coverage),'original instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
