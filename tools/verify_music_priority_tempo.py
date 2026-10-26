"""Compare PRIO/TEMPO native C with the USA ROM, including two real player updates."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held
ROOT=Path(__file__).resolve().parents[1]
PRIO,TEMPO,READER=0x0810A5D4,0x0810A5E0,0x0810A548
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
EXPECTED={i.address for a,b in [(PRIO,PRIO+10),(TEMPO,TEMPO+20)]for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}
SCALES=[0,1,127,128,255,256,257,32767,32768,65535]


def case(target,seed,value,scale=256,command=None,player=None,low=False):
    ew,iw=map(bytearray,v.fixture(seed%1000));player=v.PLAYER if player is None else player
    command=v.COMMANDS if command is None else command
    v.w16(ew,player-v.E+0x1E,scale)
    if low:command=0x01000000+seed%16
    else:ew[command-v.E]=value
    v.w32(ew,v.TRACKS-v.E+0x40,command)
    cfg=dict(address=target,native_name='Dbaa_AudioCall',arm_args=[player,v.TRACKS],
        native_args=[target|(seed&1),player,v.TRACKS,0],cover_start=READER,cover_end=TEMPO+20,
        observe_reads=[v.TRACKS+0x40,command,player+0x1C,player+0x1E,player+0x20])
    if low:cfg['extra_memory']=[(command,bytes([value]))]
    return [ew,iw],cfg


def variants(cases):
    guards=[(PRIO,255,256,None,False),(TEMPO,255,65535,None,False),
            (TEMPO,1,255,None,False),(TEMPO,255,32768,None,False),
            (TEMPO,127,256,v.TRACKS+0x40,False),(PRIO,255,256,None,True),(TEMPO,255,65535,None,True)]
    for seed,(target,value,scale,command,low)in enumerate(guards):
        ram,cfg=case(target,seed,value,scale,command=command,low=low);yield 'guards',seed,ram,cfg
    for value in range(256):
        ram,cfg=case(PRIO,value,value);yield 'priority_bytes',value,ram,cfg
        for scale in SCALES:
            ram,cfg=case(TEMPO,value,value,scale);yield 'tempo_parameters',value*65536+scale,ram,cfg
    addresses=[v.TRACKS+o for o in [0,0x1D,0x3C,0x40,0x41]]+[v.PLAYER+o for o in [0x1C,0x1D,0x1E,0x1F,0x20,0x21]]
    for target in [PRIO,TEMPO]:
        for seed,command in enumerate(addresses):
            ram,cfg=case(target,seed,255,65535,command=command);yield 'aliases',seed,ram,cfg
        for seed in range(16):
            ram,cfg=case(target,seed,255-seed,65535,low=True);yield 'filtered_sources',seed,ram,cfg
        for seed,offset in enumerate([0,0x20,0x22,0x24]):
            ram,cfg=case(target,seed,255,65535,player=v.TRACKS+offset);yield 'overlapping_structures',seed,ram,cfg
    rng=random.Random(0xA5D4A5E0)
    for seed in range(cases):
        ram,cfg=case(rng.choice([PRIO,TEMPO]),seed,rng.randrange(256),rng.randrange(65536));yield 'random',seed,ram,cfg
    parameters=[0,1,37,74,75,149,150,255]
    for route,seed,ram,cfg in held.variants(0):
        if route!='player_held_note':continue
        for variant in range(2):
            ew,iw=map(bytearray,ram);p=v.PLAYER-v.E;t=v.TRACKS-v.E
            priority=(seed*37+variant*17)&255;bias=[0,1,127,255][seed%4]
            parameter=parameters[(seed//4+variant)%8];scale=[128,255,256,65535][(seed+variant)%4]
            ew[p+9]=bias;v.w16(ew,p+0x1E,scale);v.w16(ew,p+0x20,150);v.w32(ew,p+12,0)
            v.w32(iw,v.TABLE-v.I+9*4,PRIO+1);v.w32(iw,v.TABLE-v.I+10*4,TEMPO+1)
            stream=bytes([0xBA,priority,0xBB,parameter,0xCF,60,100,0x81,0xCE,60,0x81,0xB1])
            ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=stream
            yield 'player',seed*2+variant,[ew,iw],dict(cfg,cover_start=READER,cover_end=TEMPO+20,
                priority=priority,channel_priority=min(priority+bias,255),parameter=parameter,
                interval=((parameter*2*scale)>>8)&65535,scale=scale)


def second_ram(memory,initial):
    ew=bytearray(memory[:0x40000]);iw=bytearray(initial[1])
    iw[:0x7000]=memory[0x40000:0x47000];iw[0x7800:]=memory[0x47000:]
    return [ew,iw]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_priority_tempo_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires the exact USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=0
    for index,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
            assert original==native,'RAM, reads or callback traces differ'
            assert READER in v.COVERAGE and (route=='player' or cfg['address']in v.COVERAGE),'command/reader not reached'
            if route=='player':
                assert {PRIO,TEMPO}<=v.COVERAGE,'real priority/tempo commands not reached'
                mem=original[0];p=v.PLAYER-v.E;t=v.TRACKS-v.E
                assert mem[t+0x1D]==cfg['priority'] and int.from_bytes(mem[p+0x1C:p+0x1E],'little')==cfg['parameter']*2
                assert int.from_bytes(mem[p+0x20:p+0x22],'little')==cfg['interval']
                assert v.u32(mem,p+12)==1 and v.u32(mem,t+0x40)==v.COMMANDS+8
                head=v.u32(mem,t+0x20);off=head-v.E if head<v.I else 0x40000+head-v.I
                assert head and mem[off]&0x80 and mem[off+0x13]==cfg['channel_priority'] and mem[off+0x11]==60
                # The changed interval is applied by the following player update.
                original2=v.execute(second_ram(original[0],ram),routine=cfg)
                native2=v.execute(second_ram(native[0],ram),True,routine=cfg)
                assert original2==native2,'second player update differs'
                assert v.u32(original2[0],p+12)==1+min(cfg['interval']//150,3),'tempo did not control the next update'
                results.update(original2[0]);players+=1
            assert not v.FALLBACK_TARGETS,'unexpected ARM fallback'
            error=None
        except Exception as exc:error=repr(exc)
        if error:
            failure=dict(route=route,seed=seed,index=index,error=error)
            if original and native:failure.update(rom_trace=original[1],native_trace=native[1],
                ram_offsets=[i for i,(a,b)in enumerate(zip(original[0],native[0]))if a!=b][:32])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',route,seed,error,flush=True);return 1
        counts[route]=counts.get(route,0)+1;coverage.update(v.COVERAGE&EXPECTED);results.update(original[0])
        if index%256==0:print('Passed priority/tempo cases:',index+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==13
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        parameter_bytes_tested=256,tempo_scale_edges=SCALES,real_player_cases=players,real_player_updates=players*2,
        real_commands_reached_in_every_player_case=True,note_priority_verified=True,
        tempo_interval_unsigned_product_verified=True,next_update_tempo_effect_verified=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),
        native_dll_sha256=sha(v.OUT/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'priority/tempo cases;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
