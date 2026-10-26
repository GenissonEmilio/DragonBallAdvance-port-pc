"""Compare end-tie C with the ROM and exercise real note -> end-tie player dispatch."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import random
import verify_music_player as v

ROOT=Path(__file__).resolve().parents[1]
START=0x0810AC00


def state(seed,parameter,retained,statuses,keys):
    rng=random.Random(seed+START)
    ew,iw=map(bytearray,v.fixture(seed%1000))
    t=v.TRACKS-v.E
    ew[t+5]=retained
    v.w32(ew,t+0x40,v.COMMANDS)
    ew[v.COMMANDS-v.E:v.COMMANDS-v.E+4]=bytes([parameter,0x81,0xb1,0xff])
    v.w32(ew,t+0x20,v.CHANNELS if statuses else 0)
    for index,(status,key)in enumerate(zip(statuses,keys)):
        c=v.CHANNELS-v.E+64*index
        ew[c:c+64]=bytes(rng.randrange(256)for _ in range(64))
        ew[c]=status
        ew[c+0x11]=key
        # The pitched/rhythm key deliberately differs from the original note.
        ew[c+8]=(key+17)&255
        v.w32(ew,c+0x2c,v.TRACKS)
        v.w32(ew,c+0x30,v.CHANNELS+64*(index-1)if index else 0)
        v.w32(ew,c+0x34,v.CHANNELS+64*(index+1)if index+1<len(statuses)else 0)
    reads=[v.TRACKS+0x40,v.COMMANDS,v.TRACKS+5,v.TRACKS+0x20]
    reads.extend(address+offset for address in [v.CHANNELS+64*i for i in range(len(statuses))] for offset in [0,0x11,0x34])
    return [ew,iw],reads


def event(seed,route,parameter,retained,statuses,keys):
    initial,reads=state(seed,parameter,retained,statuses,keys)
    config=dict(address=START,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[START|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=START,cover_end=START+62,observe_reads=reads)
    return route,seed,initial,config


def variants(cases):
    for status in range(256):
        # Both matching and nonmatching keys; later duplicates prove first-match stopping.
        for match in [False,True]:
            yield event(status*2+match,'status',60 if status&1 else 0x80,60,
                        [status,0x80,0x80],[60 if match else 61,60,60])
    for parameter in range(256):
        target=parameter if parameter<128 else 255
        yield event(parameter,'parameter',parameter,255,[0x80,0x80],[target,target])
    for seed in range(128):
        length=seed%8
        target=seed&127
        statuses=[0x40 if index%3==0 else 0x80 for index in range(length)]
        keys=[(target+1)&255]*length
        if length:
            keys[(seed//8)%length]=target
        yield event(seed,'lists',target if seed&1 else 0x81,target,statuses,keys)
    rng=random.Random(0xAC00)
    for seed in range(cases):
        parameter,retained=rng.randrange(256),rng.randrange(256)
        target=parameter if parameter<128 else retained
        length=rng.randrange(13)
        statuses=[rng.randrange(256)for _ in range(length)]
        keys=[rng.choice([target,rng.randrange(256)])for _ in range(length)]
        yield event(seed,'random',parameter,retained,statuses,keys)
    for seed in range(64):
        ew,iw=map(bytearray,v.fixture(seed))
        p,t=v.PLAYER-v.E,v.TRACKS-v.E
        v.w32(ew,p+0x34,0x68736d53);v.w32(ew,p+4,0);ew[p+8]=1
        v.w16(ew,p+0x20,300);v.w16(ew,p+0x22,0);v.w16(ew,p+0x24,0)
        v.w32(ew,p+0x38,0)
        ew[t]=0x8f;ew[t+1]=0;ew[t+0x17]=0;ew[t+0x19]=0;ew[t+0x1b]=0
        v.w32(ew,t+0x20,0)
        kind=[0,1,4,8][seed%4]
        ew[t+0x24:t+0x28]=bytes([kind,60,32,8])
        v.w32(ew,t+0x28,v.WAVE);v.w32(ew,t+0x2c,0x12345678)
        v.w32(ew,t+0x40,v.COMMANDS)
        # Zero-duration CF creates a held note; CE ends it in the next tick.
        stream=[0xcf,60,100,0x81,0xce]+([60]if seed&1 else [])+[0x81,0xb1]
        ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
        iw[6]=1
        v.w32(iw,0x1c,v.E+0x8000);v.w32(iw,0x38,0x0810AA01)
        v.w32(iw,v.TABLE-v.I,0x0810A4E5)
        v.w32(iw,v.TABLE-v.I+29*4,START+1)
        yield 'player_held_note',seed,[ew,iw],dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',
            arm_args=[v.PLAYER],native_args=[v.PLAYER],cover_start=START,cover_end=START+62)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512,help='random cases plus 960 directed/player cases')
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_end_tie_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM SHA-1')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};results=hashlib.sha256()
    for index,(route,seed,initial,config)in enumerate(variants(args.cases)):
        try:
            reference=v.execute(initial,routine=config);native=v.execute(initial,True,routine=config)
            error=None;equal=reference==native
        except Exception as exc:
            reference=native=None;equal=False;error=repr(exc)
        if not equal:
            failure=dict(route=route,seed=seed,index=index,error=error)
            if reference and native:
                failure.update(ram_offsets=[i for i,(a,b)in enumerate(zip(reference[0],native[0]))if a!=b][:32],
                    rom_trace=reference[1],native_trace=native[1])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',json.dumps(failure),flush=True);return 1
        counts[route]=counts.get(route,0)+1;results.update(reference[0])
        if index%256==0:print('Passed end-tie cases:',index+1,flush=True)
    assert len(v.COVERAGE)==32 and not v.FALLBACK_TARGETS & v.NATIVE_AUDIO_TARGETS
    sources=[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,original_instructions_covered=len(v.COVERAGE),
        original_instruction_addresses=[hex(a)for a in sorted(v.COVERAGE)],status_bytes_tested=256,parameter_bytes_tested=256,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=sorted(v.FALLBACK_TARGETS),
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},
        native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted((ROOT/'port/include').glob('*.h'))},
        native_dll_sha256=hashlib.sha256((v.OUT/'music_player_native.dll').read_bytes()).hexdigest(),
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),shared_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_player.py').read_bytes()).hexdigest(),
        compiler_sha256=hashlib.sha256(v.HOST_GCC.read_bytes()).hexdigest(),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional reference, not ARM7 timing or GBA hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'end-tie native/ARM cases;',len(v.COVERAGE),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
