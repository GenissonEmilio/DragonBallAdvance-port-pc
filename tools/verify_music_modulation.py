"""Compare native LFOS/MOD commands and their byte helper with the exact USA ROM."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import random
import verify_music_player as v
import verify_music_end_tie as held

ROOT=Path(__file__).resolve().parents[1]
TARGETS=(0x0810AC5C,0x0810AC68,0x0810AC7C)


def event(route,seed,target,parameter,mod_type=0,status=0x80,alias=None):
    ew,iw=map(bytearray,v.fixture(seed%1000))
    t=v.TRACKS-v.E
    ew[t]=status;ew[t+0x16]=0x91;ew[t+0x17]=0x45
    ew[t+0x18]=mod_type;ew[t+0x19]=0x67;ew[t+0x1A]=0x83
    command=v.COMMANDS if alias is None else v.TRACKS+alias
    ew[v.COMMANDS-v.E]=parameter
    v.w32(ew,t+0x40,command)
    reads=[v.TRACKS+offset for offset in [0,0x16,0x17,0x18,0x19,0x1A,0x40]]+[command]
    config=dict(address=target,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[target|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=0x0810AC40,cover_end=0x0810AC8C,
        observe_reads=reads,compare_return=target==TARGETS[0],result_register=3)
    return route,seed,[ew,iw],config


def variants(cases):
    for parameter in range(256):
        yield event('read_byte',parameter,TARGETS[0],parameter)
        for target,route in zip(TARGETS[1:],['lfo_speed','mod_depth']):
            yield event(route,parameter,target,parameter,[0,1,2,255][parameter%4])
    for status in range(256):
        for mod_type in [0,255]:
            for target in TARGETS[1:]:
                yield event('reset_flags',status*4+mod_type+(target&255),target,0,mod_type,status)
    for seed in range(4):
        for target in TARGETS:
            for alias in [0,0x16,0x17,0x18,0x19,0x1A,0x40,0x41,0x42,0x43,0x44,0x4F]:
                yield event('aliases',seed,target,0,[0,1,2,255][seed],seed*85,alias)
    rng=random.Random(0xAC68AC7C)
    for seed in range(cases):
        yield event('random',seed,rng.choice(TARGETS),rng.randrange(256),rng.randrange(256),rng.randrange(256))
    for route,seed,initial,config in held.variants(0):
        if route!='player_held_note':continue
        for reset in [False,True]:
            ew,iw=map(bytearray,initial)
            v.w16(ew,v.PLAYER-v.E+0x20,450)
            speed=[1,127,128,255][seed%4];depth=[255,128,127,1][seed%4]
            # Tick 1 creates a sustained note; tick 2 changes LFOS/MOD; tick 3 ends it.
            stream=[0xC2,speed,0xC4,depth,0xCF,60,100,0x81,
                    0xC2,0 if reset else speed,0xC4,0 if reset else depth,0x81,0xCE,60,0x81,0xB1]
            ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
            v.w32(iw,v.TABLE-v.I+17*4,TARGETS[1]+1)
            v.w32(iw,v.TABLE-v.I+19*4,TARGETS[2]+1)
            yield 'player_modulation',seed*2+reset,[ew,iw],dict(config,cover_start=0x0810AC40,cover_end=0x0810AC8C)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512,help='random cases plus 2064 directed/integration cases')
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_modulation_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM SHA-1')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};results=hashlib.sha256();players=0
    standalone_coverage=set();player_coverage=set()
    for index,(route,seed,initial,config)in enumerate(variants(args.cases)):
        try:
            if route=='player_modulation':v.COVERAGE.clear()
            reference=v.execute(initial,routine=config);native=v.execute(initial,True,routine=config)
            assert reference==native,'RAM, reads, callbacks or result differ'
            if route=='player_modulation':
                assert {0x0810AC5C,0x0810AC68,0x0810AC7C}<=v.COVERAGE,'commands not reached'
                memory=reference[0];t=v.TRACKS-v.E;head=v.u32(memory,t+0x20)
                offset=head-v.E if head<v.I else 0x40000+head-v.I
                assert head and memory[offset]&0xC0==0xC0,'held note was not released'
                assert memory[offset+0x11]==60 and memory[offset+0x10]==0
                if seed&1:assert memory[t+0x16:t+0x1B:4]==b'\0\0','modulation/phase not reset'
                players+=1
            error=None
        except Exception as exc:
            error=repr(exc)
        if error:
            (v.OUT/'failed_case.json').write_text(json.dumps(dict(route=route,seed=seed,index=index,error=error),indent=2)+'\n')
            print('FAIL:',route,seed,error,flush=True);return 1
        counts[route]=counts.get(route,0)+1;results.update(reference[0])
        if index%256==0:print('Passed modulation cases:',index+1,flush=True)
        if route=='player_modulation':
            player_coverage.update(v.COVERAGE)
        else:
            standalone_coverage.update(v.COVERAGE)
    coverage=standalone_coverage|player_coverage
    assert len(coverage)==32 and not v.FALLBACK_TARGETS
    sources=[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,helper_results_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        parameter_bytes_tested=256,status_bytes_tested=256,alias_offsets_tested=[0,0x16,0x17,0x18,0x19,0x1A,0x40,0x41,0x42,0x43,0x44,0x4F],
        real_player_cases=players,real_commands_reached_in_every_player_case=True,held_note_release_verified=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=sorted(v.FALLBACK_TARGETS),
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},
        native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted((ROOT/'port/include').glob('*.h'))},
        native_dll_sha256=hashlib.sha256((v.OUT/'music_player_native.dll').read_bytes()).hexdigest(),
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        shared_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_player.py').read_bytes()).hexdigest(),
        held_fixture_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_end_tie.py').read_bytes()).hexdigest(),
        compiler_sha256=hashlib.sha256(v.HOST_GCC.read_bytes()).hexdigest(),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional reference, not ARM7 timing or GBA hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'modulation native/ARM cases;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
