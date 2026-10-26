"""Differential PATT/PEND/REPT and filtered-reader validation against the USA ROM."""
from pathlib import Path
import argparse, ctypes, hashlib, json, random
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held

ROOT=Path(__file__).resolve().parents[1]
READER,PATT,PEND,REPT=0x0810A548,0x0810A574,0x0810A590,0x0810A5A4
REGIONS=[(READER,READER+10),(PATT,PATT+26),(PEND,PEND+20),(REPT,REPT+46)]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
EXPECTED={i.address for a,b in REGIONS for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}


def config(target,seed,command):
    return dict(address=target,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[target|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=READER,cover_end=REPT+46,
        observe_reads=[v.TRACKS,v.TRACKS+2,v.TRACKS+3,v.TRACKS+0x20,v.TRACKS+0x40,
                       *range(v.TRACKS+0x44,v.TRACKS+0x444,4),*range(command,command+5)],
        compare_return=target==READER,result_register=3)


def case(target,seed,depth=0,count=2,repeat=0,offset=None,low=False):
    ew,iw=map(bytearray,v.fixture(seed%1000));t=v.TRACKS-v.E
    # PEND faithfully indexes any byte depth; the original has no upper guard.
    for n in range(256):v.w32(ew,t+0x44+4*n,v.COMMANDS+4*n)
    ew[t+2]=depth;ew[t+3]=repeat;v.w32(ew,t+0x20,0)
    command=v.COMMANDS if offset is None else v.TRACKS+offset
    if low:command=0x01000000+seed%16
    contents=bytes([count])+int(v.COMMANDS+0x88).to_bytes(4,'little')
    if target==PATT:contents=int(v.COMMANDS+0x88).to_bytes(4,'little')
    if not low:ew[command-v.E:command-v.E+len(contents)]=contents
    v.w32(ew,t+0x40,command)
    cfg=config(target,seed,command)
    if low:cfg['extra_memory']=[(command,contents)]
    return [ew,iw],cfg


def variants(cases):
    # Small directed cases keep every negative regression gate fast.
    directed=[(PATT,dict(depth=0)),(PATT,dict(depth=3)),(PATT,dict(depth=1)),
              (PEND,dict(depth=1)),(PEND,dict(depth=3)),
              (REPT,dict(repeat=255,count=255)),(REPT,dict(repeat=0,count=2)),
              (REPT,dict(repeat=0,count=1)),(REPT,dict(count=0)),
              (READER,dict(offset=0x40))]
    for seed,(target,kw)in enumerate(directed):
        ram,cfg=case(target,seed,**kw);yield 'guards',seed,ram,cfg
    for depth in range(256):
        for target,route in [(PATT,'pattern_depth'),(PEND,'return_depth')]:
            ram,cfg=case(target,depth,depth=depth);yield route,depth,ram,cfg
    for repeat in range(256):
        for count in [0,1,2,3,127,128,254,255]:
            ram,cfg=case(REPT,repeat,repeat=repeat,count=count)
            yield 'repeat_counter',repeat*256+count,ram,cfg
    for count in range(256):
        ram,cfg=case(REPT,count,repeat=(count+253)&255,count=count)
        yield 'repeat_count',count,ram,cfg
        ram,cfg=case(READER,count,count=count);yield 'reader_bytes',count,ram,cfg
    for target in [PATT,REPT,READER]:
        for seed in range(16):
            ram,cfg=case(target,seed,depth=seed%3,repeat=seed%4,count=255,low=True)
            yield 'filtered_sources',seed,ram,cfg
    for target in [PATT,REPT,READER]:
        for seed,offset in enumerate([0,2,3,0x20,0x3C,0x40,0x41,0x44,0x48,0x4C]):
            ram,cfg=case(target,seed,depth=seed%3,repeat=seed%4,count=3,offset=offset)
            yield 'aliases',seed,ram,cfg
    rng=random.Random(0xA574A5A4)
    for seed in range(cases):
        target=rng.choice([PATT,PEND,REPT,READER])
        ram,cfg=case(target,seed,depth=rng.randrange(256),repeat=rng.randrange(256),count=rng.randrange(256))
        yield 'random',seed,ram,cfg
    for route,seed,ram,cfg in held.variants(0):
        if route!='player_held_note':continue
        for kind in range(6):
            ew,iw=map(bytearray,ram);t=v.TRACKS-v.E
            ew[t+2]=0;ew[t+3]=0;v.w16(ew,v.PLAYER-v.E+0x20,150)
            for index,target in [(2,PATT),(3,PEND),(4,REPT)]:v.w32(iw,v.TABLE-v.I+index*4,target+1)
            base=v.COMMANDS;branches=[base+0x100,base+0x140,base+0x180]
            def write(address,stream):ew[address-v.E:address-v.E+len(stream)]=bytes(stream)
            if kind<3:
                levels=kind+1
                write(base,[0xB3,*branches[0].to_bytes(4,'little'),0xCE,60,0x81,0xB1])
                for n in range(levels):
                    stream=[0xB3,*branches[n+1].to_bytes(4,'little'),0xB4]if n+1<levels else[0xCF,60,100,0xB4]
                    write(branches[n],stream)
                expected_cursor=base+8;needed={PATT,PEND};overflow=False
            elif kind==3:
                ew[t+2]=3
                write(base,[0xCF,60,100,0xB3,*branches[0].to_bytes(4,'little')])
                write(branches[0],[0xB4,0x81,0xB1])
                expected_cursor=base+4;needed={PATT};overflow=True
            elif kind==4:
                count=1+seed%3
                write(base,[0xCF,60,100,0xB5,count,*base.to_bytes(4,'little'),0xCE,60,0x81,0xB1])
                expected_cursor=base+12;needed={REPT,READER};overflow=False
            else:
                write(base,[0xB5,0,*branches[0].to_bytes(4,'little')])
                write(branches[0],[0xCF,60,100,0xCE,60,0x81,0xB1])
                expected_cursor=branches[0]+6;needed={REPT};overflow=False
            yield 'player',seed*6+kind,[ew,iw],dict(cfg,cover_start=READER,cover_end=REPT+46,
                expected_cursor=expected_cursor,needed=needed,overflow=overflow,levels=kind+1 if kind<3 else 0)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_patterns_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires the exact USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=0;levels=set()
    for index,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
            assert original==native,'RAM, filtered reader result, reads or callback traces differ'
            assert not v.FALLBACK_TARGETS,'unexpected ARM fallback'
            if route=='player':
                assert cfg['needed']<=v.COVERAGE,'real pattern command not reached'
                mem=original[0];t=v.TRACKS-v.E
                assert v.u32(mem,t+0x40)==cfg['expected_cursor'],'wrong final stream position'
                if cfg['overflow']:
                    assert mem[t]==0 and not v.u32(mem,t+0x20),'overflow did not end/unlink track'
                else:
                    head=v.u32(mem,t+0x20);off=head-v.E if head<v.I else 0x40000+head-v.I
                    assert head and mem[off]&0xC0==0xC0 and mem[off+0x11]==60 and mem[off+0x10]==0
                    assert mem[t+2]==mem[t+3]==0,'return or repeat counter not restored'
                players+=1
                if cfg['levels']:levels.add(cfg['levels'])
            error=None
        except Exception as exc:error=repr(exc)
        if error:
            failure=dict(route=route,seed=seed,index=index,error=error)
            if original and native:failure.update(rom_trace=original[1],native_trace=native[1],
                ram_offsets=[i for i,(a,b)in enumerate(zip(original[0],native[0]))if a!=b][:32])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',route,seed,error,flush=True);return 1
        counts[route]=counts.get(route,0)+1;coverage.update(v.COVERAGE&EXPECTED);results.update(original[0])
        if index%256==0:print('Passed pattern cases:',index+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==50 and levels=={1,2,3}
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,reader_results_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        depth_bytes_tested=256,repeat_bytes_tested=256,count_bytes_tested=256,real_player_cases=players,
        real_commands_reached_in_every_player_case=True,nested_pattern_levels=sorted(levels),
        return_cursors_verified=True,overflow_track_end_verified=True,held_notes_verified=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),
        native_dll_sha256=sha(v.OUT/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),
        host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),results_sha256=results.hexdigest(),
        byte_matching=False,full_game_boot=False,cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'pattern cases;',len(coverage),'original instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
