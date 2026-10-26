"""Compare MODT native C with the ROM and verify pitch/volume/pan transitions."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held
import verify_music_priority_tempo as pt
from verify_music_pitch_bend import field,signed,check_pitch
from verify_music_pan import check_volumes
ROOT=Path(__file__).resolve().parents[1]
START,READER=0x0810A694,0x0810A548
EXPECTED={i.address for i in Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(v.ROM[0x10A694:0x10A6AC],START)}


def command_case(seed,value,old,status=0x80,offset=None,low=False):
    ew,iw=map(bytearray,v.fixture(seed%1000));t=v.TRACKS-v.E
    ew[t]=status;ew[t+0x18]=old;ew[t+0x16]=0xE2;ew[t+0x1A]=0xC4;ew[t+0x1C]=0x91
    command=v.COMMANDS if offset is None else v.TRACKS+offset
    if low:command=0x01000000+seed%16
    else:ew[command-v.E]=value
    v.w32(ew,t+0x40,command)
    cfg=dict(address=START,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[START|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=READER,cover_end=START+24,
        observe_reads=[v.TRACKS+0x40,command,v.TRACKS,v.TRACKS+0x18,v.TRACKS+0x1C,v.TRACKS+0x1A])
    if low:cfg['extra_memory']=[(command,bytes([value]))]
    return [ew,iw],cfg


def variants(cases):
    guards=[(255,0,0x80,None,False),(2,2,0x80,None,False),(0,1,0,None,False),
            (255,0,0x80,None,True),(127,127,0x83,0x40,False)]
    for seed,(value,old,status,offset,low)in enumerate(guards):
        ram,cfg=command_case(seed,value,old,status,offset,low);yield 'guards',seed,ram,cfg
    for value in range(256):
        for old in [value,value^0x80]:
            for status in [0,0x80]:
                ram,cfg=command_case(value,value,old,status);yield 'parameters',value*65536+old*256+status,ram,cfg
    for status in range(256):
        value=(status*73)&255
        for old in [value,value^1]:
            ram,cfg=command_case(status,value,old,status);yield 'status_bytes',status*256+old,ram,cfg
    for offset in [0,0x16,0x17,0x18,0x19,0x1A,0x1B,0x1C,0x20,0x40,0x41,0x43]:
        for value in [0,1,127,128,254,255]:
            ram,cfg=command_case(offset+value,value,value^(offset&1),0x83,offset);yield 'aliases',offset*256+value,ram,cfg
    for seed in range(16):
        ram,cfg=command_case(seed,255-seed,seed%3,(seed*17)&255,low=True);yield 'filtered_sources',seed,ram,cfg
    rng=random.Random(0xA694C0)
    for seed in range(cases):
        ram,cfg=command_case(seed,rng.randrange(256),rng.randrange(256),rng.randrange(256));yield 'random',seed,ram,cfg
    fixtures=[ram for route,seed,ram,cfg in held.variants(0)if route=='player_held_note']
    for value in range(256):
        priors={value,value^1}
        if value in [0,1,2,255]:priors.update([0,1,2,255])
        for old in sorted(priors):
            for live in [False,True]:
                seed=value*512+old*2+live;ew,iw=map(bytearray,fixtures[seed%64]);t=v.TRACKS-v.E;p=v.PLAYER-v.E
                kind=[0,1,4,8][(value+old+int(live))%4]
                phase=192 if (value+old+int(live))&1 else 12
                ew[t]=0x8F;ew[t+8:t+0x10]=bytes(8);ew[t+0x0C]=2;ew[t+0x0D]=5
                ew[t+0x12]=96;ew[t+0x13]=64;ew[t+0x14]=12;ew[t+0x15]=252
                ew[t+0x16]=224 if phase==192 else 6;ew[t+0x17]=32;ew[t+0x18]=old
                ew[t+0x19]=4;ew[t+0x1A]=phase;ew[t+0x1B]=0;ew[t+0x1C]=0
                ew[t+0x24]=kind;v.w16(ew,p+0x20,150);v.w32(ew,p+12,0)
                v.w32(iw,v.TABLE-v.I+20*4,START+1)
                stream=([0xCF,60,100,0x81,0xC5,value,0x81]if live else[0xC5,value,0xCF,60,100,0x81,0x81])
                ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
                cfg=dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',arm_args=[v.PLAYER],native_args=[v.PLAYER],
                    cover_start=READER,cover_end=START+24,parameter=value,old=old,kind=kind,live=live,phase=phase)
                yield 'player_live'if live else'player_create',seed,[ew,iw],cfg


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_mod_type_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=updates=same=changed=cross=0
    for index,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            if route.startswith('player_'):
                rom_ram=native_ram=ram;head=first=None
                for step in range(2):
                    original=v.execute(rom_ram,routine=cfg);native=v.execute(native_ram,True,routine=cfg)
                    assert original==native,'player RAM, reads or callbacks differ'
                    memory=original[0];current=field(memory,v.TRACKS+0x20,4)
                    assert current and field(memory,current)&0x80 and field(memory,current+8)==60
                    if head is None:head=current;first=memory
                    else:assert current==head,'mode change replaced note channel'
                    mode=cfg['old']if cfg['live']and step==0 else cfg['parameter']
                    assert field(memory,v.TRACKS+0x18)==mode,'modulation type was clamped or not stored'
                    phase=cfg['phase']+4*(step+1)
                    triangle=phase if phase<64 else 128-phase if phase<192 else phase-256
                    assert field(memory,v.TRACKS+0x1A)==phase and field(memory,v.TRACKS+0x16)==(triangle//2)&255,'mode change reset LFO phase/value'
                    assert field(memory,v.TRACKS+0x1B)==field(memory,v.TRACKS+0x1C)==0
                    check_pitch(memory);check_volumes(memory,head)
                    for off,width in [(1,1),(4,4),(8,1),(0x24,4)]:
                        assert field(memory,head+off,width)==field(first,head+off,width),'mode changed instrument/key/envelope'
                    results.update(memory);updates+=1
                    rom_ram=pt.second_ram(memory,ram);native_ram=pt.second_ram(native[0],ram)
                assert {START,READER}<=v.COVERAGE,'MODT/reader not reached'
                coarse,fine=check_pitch(memory);key=max(60+signed(coarse),0);ctype=cfg['kind']&7
                target=0x0810B78C if ctype else 0x0810AC90
                freq_cfg=dict(address=target,native_name='Dbaa_AudioCall',arm_args=[ctype if ctype else v.WAVE,key,fine],
                    native_args=[],cover_start=target,cover_end=target+180,compare_return=True)
                frequency=v.execute(pt.second_ram(memory,ram),routine=freq_cfg)[2]
                assert field(memory,head+0x20,4)==frequency,'independent PCM/CGB frequency differs'
                if ctype:
                    required=3 if cfg['live']and cfg['old']!=cfg['parameter']else 1 if cfg['parameter']else 2
                    assert field(memory,head+0x1D)==(field(first,head+0x1D)|required),'CGB propagation flags differ'
                assert field(memory,v.PLAYER+12,4)==2
                same+=cfg['old']==cfg['parameter'];changed+=cfg['old']!=cfg['parameter']
                cross+=cfg['old']in[0,1,2,255]and cfg['parameter']in[0,1,2,255]
                players+=1
            else:
                original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
                assert original==native,'command RAM, reads or callbacks differ'
                assert {START,READER}<=v.COVERAGE,'command/reader not reached'
            assert not v.FALLBACK_TARGETS,'unexpected ARM fallback'
            error=None
        except Exception as exc:error=repr(exc)
        if error:
            failure=dict(route=route,seed=seed,index=index,error=error)
            if original and native:failure.update(rom_trace=original[1],native_trace=native[1],ram_offsets=[i for i,(a,b)in enumerate(zip(original[0],native[0]))if a!=b][:32])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',route,seed,error,flush=True);return 1
        counts[route]=counts.get(route,0)+1;coverage.update(v.COVERAGE&EXPECTED);results.update(original[0])
        if index%256==0:print('Passed modulation-type cases:',index+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==11
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        parameter_bytes_tested=256,status_bytes_tested=256,real_player_cases=players,real_player_updates=updates,
        unchanged_type_player_cases=same,changed_type_player_cases=changed,cross_mode_player_cases=cross,
        real_commands_reached_in_every_player_case=True,unsigned_type_and_unknown_modes_verified=True,
        unchanged_type_preserves_flags=True,changed_type_requests_all_recalculations=True,
        phase_modulation_and_delay_preserved=True,pitch_volume_pan_transitions_verified=True,
        pitch_compared_to_independent_arithmetic=True,volume_compared_to_independent_arithmetic=True,
        instrument_and_note_key_preserved=True,pcm_cgb_propagation_flags_verified=True,
        frequency_compared_to_independent_rom_call=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),player_sequence_tool_sha256=sha(ROOT/'tools/verify_music_priority_tempo.py'),
        pitch_oracle_tool_sha256=sha(ROOT/'tools/verify_music_pitch_bend.py'),volume_oracle_tool_sha256=sha(ROOT/'tools/verify_music_pan.py'),
        native_dll_sha256=sha(v.OUT/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'modulation-type cases;',updates,'player updates;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
