"""Compare VOL C with the USA ROM, including note creation and live volume changes."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held
import verify_music_priority_tempo as pt
ROOT=Path(__file__).resolve().parents[1]
START,READER=0x0810A638,0x0810A548
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
EXPECTED={i.address for i in MD.disasm(v.ROM[0x10A638:0x10A64A],START)}


def command_case(seed,value,status=0x80,offset=None,low=False):
    ew,iw=map(bytearray,v.fixture(seed%1000));t=v.TRACKS-v.E
    ew[t]=status;command=v.COMMANDS if offset is None else v.TRACKS+offset
    if low:command=0x01000000+seed%16
    else:ew[command-v.E]=value
    v.w32(ew,t+0x40,command)
    cfg=dict(address=START,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[START|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=READER,cover_end=START+18,
        observe_reads=[v.TRACKS+0x40,command,v.TRACKS])
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
    for offset in [0,0x12,0x13,0x10,0x11,0x14,0x18,0x20,0x40,0x41]:
        for value in [0,1,127,128,254,255]:
            ram,cfg=command_case(offset+value,value,0x83,offset);yield 'aliases',offset*256+value,ram,cfg
    for seed in range(16):
        ram,cfg=command_case(seed,255-seed,(seed*17)&255,low=True);yield 'filtered_sources',seed,ram,cfg
    rng=random.Random(0xA638BE)
    for seed in range(cases):
        ram,cfg=command_case(seed,rng.randrange(256),rng.randrange(256));yield 'random',seed,ram,cfg
    fixtures=[ram for route,seed,ram,cfg in held.variants(0)if route=='player_held_note']
    for value in range(256):
        for live in [False,True]:
            ew,iw=map(bytearray,fixtures[(value+int(live))%64]);t=v.TRACKS-v.E;p=v.PLAYER-v.E
            kind=[0,1,4,8][(value+int(live))%4]
            ew[t]=0x8F;ew[t+8:t+0x10]=bytes(8)
            for offset in [0x16,0x17,0x18,0x19,0x1B]:ew[t+offset]=0
            ew[t+0x13]=[0,1,32,64,127,255][value%6]
            ew[t+0x14]=[0,64,192,127,128,255][value%6]
            ew[t+0x15]=[0,127,128,255][value%4]
            ew[t+0x18]=value%3;ew[t+0x16]=(value*73)&255
            ew[t+0x24]=kind;v.w16(ew,p+0x20,150);v.w32(ew,p+12,0)
            v.w32(iw,v.TABLE-v.I+13*4,START+1)
            stream=([0xCF,60,100,0x81,0xBE,value,0x81,0xCE,60,0x81,0xB1]if live else
                    [0xBE,value,0xCF,60,100,0x81,0xCE,60,0x81,0xB1])
            ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
            cfg=dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',arm_args=[v.PLAYER],native_args=[v.PLAYER],
                cover_start=READER,cover_end=START+18,parameter=value,kind=kind,live=live)
            yield 'player_live'if live else'player_create',value,[ew,iw],cfg


def field(memory,address,width=1):
    offset=address-v.E if address<v.I else 0x40000+address-v.I
    return int.from_bytes(memory[offset:offset+width],'little')


def check_volumes(memory,head):
    def signed(value):return value-256 if value&128 else value
    raw=field(memory,v.TRACKS+0x12);master=field(memory,v.TRACKS+0x13)
    volume=raw*master>>5
    kind=field(memory,v.TRACKS+0x18);mod=signed(field(memory,v.TRACKS+0x16))
    if kind==1:volume=(mod+128)*volume>>7
    pan=2*signed(field(memory,v.TRACKS+0x14))+signed(field(memory,v.TRACKS+0x15))
    if kind==2:pan+=mod
    pan=max(-128,min(127,pan))
    right=((pan+128)*volume>>8)&255;left=((127-pan)*volume>>8)&255
    assert field(memory,v.TRACKS+0x10)==right and field(memory,v.TRACKS+0x11)==left,'track volume arithmetic differs'
    velocity=field(memory,head+0x12);channel_pan=signed(field(memory,head+0x14))
    right=min(255,(128+channel_pan)*velocity*right>>14)
    left=min(255,(127-channel_pan)*velocity*left>>14)
    assert field(memory,head+2)==right and field(memory,head+3)==left,'channel volume arithmetic differs'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_volume_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=0
    for index,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
            assert original==native,'RAM, reads or callbacks differ'
            if route.startswith('player_'):
                first=original[0];head=field(first,v.TRACKS+0x20,4)
                assert head and field(first,head)&0x80 and field(first,head+8)==60,'note not created'
                original2=v.execute(pt.second_ram(original[0],ram),routine=cfg)
                native2=v.execute(pt.second_ram(native[0],ram),True,routine=cfg)
                assert original2==native2,'second player update differs'
                assert {START,READER}<=v.COVERAGE,'VOL/filtered reader not reached'
                second=original2[0];assert field(second,v.TRACKS+0x20,4)==head,'note channel replaced'
                active=second if cfg['live']else first
                value=cfg['parameter']
                assert field(active,v.TRACKS+0x12)==value,'volume byte differs'
                assert field(second,v.PLAYER+12,4)==2
                check_volumes(active,head)
                if cfg['live']:
                    assert field(second,v.TRACKS+0x40,4)==v.COMMANDS+7
                    for off,width in [(1,1),(4,4),(8,1),(0x20,4),(0x24,4)]:
                        assert field(second,head+off,width)==field(first,head+off,width),'volume changed pitch or instrument'
                    if cfg['kind']&7:assert field(second,head+0x1D)==(field(first,head+0x1D)|1),'CGB volume update flag missing'
                else:assert field(first,v.TRACKS+0x40,4)==v.COMMANDS+6
                results.update(second);players+=1
            else:assert {START,READER}<=v.COVERAGE,'command/reader not reached'
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
        if index%256==0:print('Passed volume cases:',index+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==8
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        parameter_bytes_tested=256,status_bytes_tested=256,real_player_cases=players,real_player_updates=players*2,
        real_commands_reached_in_every_player_case=True,unsigned_volume_byte_verified=True,volume_flags_verified=True,
        note_creation_volume_verified=True,existing_note_volume_update_verified=True,
        cgb_volume_update_flag_verified=True,pitch_and_instrument_preserved=True,
        volume_compared_to_independent_arithmetic=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),
        player_sequence_tool_sha256=sha(ROOT/'tools/verify_music_priority_tempo.py'),
        native_dll_sha256=sha(v.OUT/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'volume cases;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
