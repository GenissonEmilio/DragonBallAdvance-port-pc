"""Compare LFODL native C with the ROM, including note-start and live delay timing."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held
import verify_music_priority_tempo as pt
ROOT=Path(__file__).resolve().parents[1]
START,READER=0x0810A688,0x0810A548
EXPECTED={i.address for i in Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(v.ROM[0x10A688:0x10A692],START)}


def command_case(seed,value,status=0x80,offset=None,low=False):
    ew,iw=map(bytearray,v.fixture(seed%1000));t=v.TRACKS-v.E
    ew[t]=status;ew[t+0x16]=0x63;ew[t+0x1A]=0x41;ew[t+0x1C]=0x91
    command=v.COMMANDS if offset is None else v.TRACKS+offset
    if low:command=0x01000000+seed%16
    else:ew[command-v.E]=value
    v.w32(ew,t+0x40,command)
    cfg=dict(address=START,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[START|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=READER,cover_end=START+10,
        observe_reads=[v.TRACKS+0x40,command,v.TRACKS,v.TRACKS+0x1C,v.TRACKS+0x1A])
    if low:cfg['extra_memory']=[(command,bytes([value]))]
    return [ew,iw],cfg


def variants(cases):
    guards=[(255,0x80,None,False),(128,0,None,False),(0,0xF3,None,False),
            (255,0x80,None,True),(127,0x80,0x40,False)]
    for seed,(value,status,offset,low)in enumerate(guards):
        ram,cfg=command_case(seed,value,status,offset,low);yield 'guards',seed,ram,cfg
    for value in range(256):
        for status in [0,0x80,0xF3,0xFF]:
            ram,cfg=command_case(value,value,status);yield 'parameters',value*256+status,ram,cfg
    for status in range(256):
        ram,cfg=command_case(status,(status*73)&255,status);yield 'status_bytes',status,ram,cfg
    for offset in [0,0x16,0x17,0x18,0x19,0x1A,0x1B,0x1C,0x20,0x40,0x41,0x43]:
        for value in [0,1,127,128,254,255]:
            ram,cfg=command_case(offset+value,value,0x83,offset);yield 'aliases',offset*256+value,ram,cfg
    for seed in range(16):
        ram,cfg=command_case(seed,255-seed,(seed*17)&255,low=True);yield 'filtered_sources',seed,ram,cfg
    rng=random.Random(0xA688C0)
    for seed in range(cases):
        ram,cfg=command_case(seed,rng.randrange(256),rng.randrange(256));yield 'random',seed,ram,cfg
    fixtures=[ram for route,seed,ram,cfg in held.variants(0)if route=='player_held_note']
    for value in range(256):
        for live in [False,True]:
            ew,iw=map(bytearray,fixtures[(value+int(live))%64]);t=v.TRACKS-v.E;p=v.PLAYER-v.E
            kind=[0,1,4,8][(value+int(live))%4]
            ew[t]=0x8F;ew[t+8:t+0x10]=bytes(8)
            ew[t+0x16]=6;ew[t+0x17]=32;ew[t+0x18]=value%2
            ew[t+0x19]=4;ew[t+0x1A]=12;ew[t+0x1B]=3;ew[t+0x1C]=0x91
            ew[t+0x24]=kind;v.w16(ew,p+0x20,150);v.w32(ew,p+12,0)
            v.w32(iw,v.TABLE-v.I+18*4,START+1)
            stream=([0xCF,60,100,0x81,0xC3,value]if live else[0xC3,value,0xCF,60,100])+[0x81]*300
            ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
            cfg=dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',arm_args=[v.PLAYER],native_args=[v.PLAYER],
                cover_start=READER,cover_end=START+10,parameter=value,kind=kind,live=live)
            yield 'player_live'if live else'player_create',value,[ew,iw],cfg


def field(memory,address,width=1):
    offset=address-v.E if address<v.I else 0x40000+address-v.I
    return int.from_bytes(memory[offset:offset+width],'little')


def signed(value):return value-256 if value&128 else value


def check_pitch(memory):
    t=v.TRACKS
    pitch=4*(signed(field(memory,t+0x0C))+signed(field(memory,t+0x0E))*field(memory,t+0x0F))
    pitch+=256*(signed(field(memory,t+0x0A))+signed(field(memory,t+0x0B)))+field(memory,t+0x0D)
    if field(memory,t+0x18)==0:pitch+=16*signed(field(memory,t+0x16))
    coarse,fine=(pitch//256)&255,pitch&255
    assert field(memory,t+8)==coarse and field(memory,t+9)==fine,'independent pitch differs'
    return coarse,fine


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_lfo_delay_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=updates=timing_ticks=0
    for index,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            if route.startswith('player_'):
                value=cfg['parameter'];live=cfg['live']
                schedule=[1,1,1,1]if live else[1,max(1,value-1),1]
                delay=3 if live else value;phase,modulation=(0,0)if delay else(12,6)
                rom_ram=native_ram=ram;head=None;first=None
                for step,ticks in enumerate(schedule):
                    for state in [rom_ram,native_ram]:v.w16(state[0],v.PLAYER-v.E+0x20,150*ticks)
                    original=v.execute(rom_ram,routine=cfg);native=v.execute(native_ram,True,routine=cfg)
                    assert original==native,'player RAM, reads or callbacks differ'
                    memory=original[0];current_head=field(memory,v.TRACKS+0x20,4)
                    assert current_head and field(memory,current_head)&0x80 and field(memory,current_head+8)==60
                    if head is None:head=current_head;first=memory
                    else:assert current_head==head,'delay changed note channel'
                    for tick in range(ticks):
                        if delay:delay-=1
                        else:
                            phase+=4
                            assert phase<64,'timing fixture exceeded independent rising-wave domain'
                            modulation=phase//2
                    assert field(memory,v.TRACKS+0x1C)==delay,'delay countdown/onset differs'
                    assert field(memory,v.TRACKS+0x1A)==phase and field(memory,v.TRACKS+0x16)==modulation,'LFO phase/modulation differs'
                    assert field(memory,v.TRACKS+0x1B)==(3 if live and step==0 else value),'preset differs'
                    check_pitch(memory)
                    if live and step in [1,2]:
                        assert field(memory,head+0x20,4)==field(first,head+0x20,4),'live delay changed frequency early'
                        assert field(memory,head+0x1D)==field(first,head+0x1D),'live delay requested CGB update early'
                    for off,width in [(1,1),(4,4),(8,1),(0x24,4)]:
                        assert field(memory,head+off,width)==field(first,head+off,width),'delay changed instrument/key/envelope'
                    results.update(memory);updates+=1;timing_ticks+=ticks
                    rom_ram=pt.second_ram(memory,ram);native_ram=pt.second_ram(native[0],ram)
                assert {START,READER}<=v.COVERAGE,'LFODL/reader not reached'
                coarse,fine=check_pitch(memory);key=max(60+signed(coarse),0);ctype=cfg['kind']&7
                target=0x0810B78C if ctype else 0x0810AC90
                freq_cfg=dict(address=target,native_name='Dbaa_AudioCall',arm_args=[ctype if ctype else v.WAVE,key,fine],
                    native_args=[],cover_start=target,cover_end=target+180,compare_return=True)
                frequency=v.execute(pt.second_ram(memory,ram),routine=freq_cfg)[2]
                assert field(memory,head+0x20,4)==frequency,'independent PCM/CGB frequency differs'
                if ctype:
                    required=1 if value%2 else 2
                    assert field(memory,head+0x1D)==(field(first,head+0x1D)|required),'CGB modulation flag differs'
                assert field(memory,v.PLAYER+12,4)==sum(schedule),'player tick count differs'
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
        if index%256==0:print('Passed LFO-delay cases:',index+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==4
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        parameter_bytes_tested=256,status_bytes_tested=256,real_player_cases=players,real_player_updates=updates,real_player_ticks=timing_ticks,
        real_commands_reached_in_every_player_case=True,unsigned_preset_verified=True,
        live_counter_phase_and_flags_preserved=True,note_start_load_and_reset_verified=True,
        zero_delay_preserves_note_start_phase=True,countdown_and_first_modulation_tick_verified=True,
        maximum_255_delay_verified=True,pitch_compared_to_independent_arithmetic=True,
        instrument_and_note_key_preserved=True,pcm_cgb_and_pitch_volume_modulation_verified=True,
        frequency_compared_to_independent_rom_call=True,cgb_modulation_flags_verified=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),player_sequence_tool_sha256=sha(ROOT/'tools/verify_music_priority_tempo.py'),
        native_dll_sha256=sha(v.OUT/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'LFO-delay cases;',updates,'player updates;',timing_ticks,'ticks;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
