"""Compare VOICE C with the ROM, including timbre selection and PCM/CGB notes."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held
import verify_music_priority_tempo as pt
from verify_music_key_shift import field
ROOT=Path(__file__).resolve().parents[1]
START=0x0810A608
BANK,CHILDREN,KEYMAP=v.E+0x12000,v.E+0x16000,v.E+0x18000
EXPECTED={i.address for i in Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(v.ROM[0x10A608:0x10A636],START)}
PLAYER_FIXTURES=None


def command_case(seed,index,status=0x80,source=None,command=None,low_command=False,player=None):
    ew,iw=map(bytearray,v.fixture(seed%1000));t=v.TRACKS-v.E
    ew[t]=status;player=v.PLAYER if player is None else player
    source=BANK+12*index if source is None else source
    command=v.COMMANDS if command is None else command
    extra=[]
    values=[0x12345678^(seed*17),0x89ABCDEF^seed,0xFEDCBA98^(seed*7)]
    if v.E<=source<v.E+len(ew)-12:
        for n,value in enumerate(values):v.w32(ew,source-v.E+4*n,value)
    elif source< v.E:
        # Map only the page below EWRAM; the last two words may cross into EWRAM.
        data=b''.join(value.to_bytes(4,'little')for value in values)
        below=min(12,v.E-source);extra.append((source,data[:below]))
        if below<12:ew[:12-below]=data[below:]
    elif not 0x08000000<=source<0x09000000:raise ValueError(hex(source))
    v.w32(ew,player-v.E+0x30,(source-12*index)&0xFFFFFFFF)
    v.w32(ew,t+0x40,command)
    if low_command:extra.append((command,bytes([index])))
    else:ew[command-v.E]=index
    cfg=dict(address=START,native_name='Dbaa_AudioCall',arm_args=[player,v.TRACKS],
        native_args=[START|(seed&1),player,v.TRACKS,0],cover_start=START,cover_end=START+46,
        observe_reads=list({v.TRACKS+0x40,command,player+0x30,source,source+4,source+8}))
    if extra:cfg['extra_memory']=extra
    return [ew,iw],cfg


def player_case(index,switch=False):
    global PLAYER_FIXTURES
    if PLAYER_FIXTURES is None:
        PLAYER_FIXTURES=[ram for route,seed,ram,cfg in held.variants(0)if route=='player_held_note']
    fixture=PLAYER_FIXTURES[index%64]
    ew,iw=map(bytearray,fixture);t=v.TRACKS-v.E;p=v.PLAYER-v.E
    ew[t]=0x8F;ew[t+8:t+0x10]=bytes(8)
    for offset in [0x16,0x17,0x18,0x19,0x1B]:ew[t+offset]=0
    v.w16(ew,p+0x20,150);v.w32(ew,p+12,0);v.w32(ew,p+0x30,BANK)
    v.w32(iw,v.TABLE-v.I+12*4,START+1);iw[6]=3
    for n in range(256):
        kind=0 if switch else [0,1,4,8,0x40,0x80,0xC0][n%7]
        wave=v.WAVE+0x100*(n%16);v.w32(ew,wave-v.E+4,0x400000+0x10000*n)
        tone=bytes([kind,40+n%40,20+n%64,8])+wave.to_bytes(4,'little')+(0x12340000+n).to_bytes(4,'little')
        if kind&0xC0:tone=tone[:4]+CHILDREN.to_bytes(4,'little')+KEYMAP.to_bytes(4,'little')
        ew[BANK-v.E+12*n:BANK-v.E+12*n+12]=tone
        ctype=[0,1,4,8][n%4]
        child=bytes([ctype,40+n%40,20+n%64,0xD0])+v.WAVE.to_bytes(4,'little')+(0x56780000+n).to_bytes(4,'little')
        ew[CHILDREN-v.E+12*n:CHILDREN-v.E+12*n+12]=child
        ew[KEYMAP-v.E+n]=(n+27)&255
    stream=([0xBD,index,0xCF,60,100,0x81,0xBD,(index+1)&255,0xCF,62,90,0x81,0xB1]if switch else
            [0xBD,index,0xCF,60,100,0x81,0xCE,60,0x81,0xB1])
    ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
    cfg=dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',arm_args=[v.PLAYER],native_args=[v.PLAYER],
        cover_start=START,cover_end=START+46,parameter=index,switch=switch)
    return [ew,iw],cfg


def variants(cases):
    # Guards come first so negative controls fail without running the full corpus.
    for seed,kwargs in enumerate([dict(index=255),dict(index=7,source=v.E-4),dict(index=3,source=v.TRACKS+0x20),
        dict(index=4,command=0x01000000,low_command=True),dict(index=0,player=v.TRACKS+0x10)]):
        ram,cfg=command_case(seed,**kwargs);yield 'guards',seed,ram,cfg
    for index in range(256):
        for status in [0,0x80,0xF3,0xFF]:
            ram,cfg=command_case(index,index,status);yield 'instruments',index*256+status,ram,cfg
    for status in range(256):
        ram,cfg=command_case(status,(status*73)&255,status);yield 'status_bytes',status,ram,cfg
    for offset in [0,0x1C,0x20,0x24,0x28,0x2C,0x30,0x38,0x3C,0x40,0x44]:
        for index in [0,1,127,128,254,255]:
            ram,cfg=command_case(offset+index,index,source=v.TRACKS+offset);yield 'aliases',offset*256+index,ram,cfg
    for index in [0,1,127,128,254,255]:
        for source in [v.E-12,v.E-8,v.E-4,v.E,v.E+4]:
            ram,cfg=command_case(index,index,source=source);yield 'filter_boundaries',index*256+(source&255),ram,cfg
        ram,cfg=command_case(index,index,command=0x01000000,low_command=True);yield 'raw_parameters',index,ram,cfg
    for index in range(64):
        ram,cfg=command_case(index,index,source=0x08A69000+12*index);yield 'rom_voices',index,ram,cfg
    rng=random.Random(START)
    for seed in range(cases):
        ram,cfg=command_case(seed,rng.randrange(256),rng.randrange(256));yield 'random',seed,ram,cfg
    for index in range(256):
        ram,cfg=player_case(index);yield 'player_create',index,ram,cfg
    for index in range(64):
        ram,cfg=player_case(index,True);yield 'player_switch',index,ram,cfg


def check_note(memory,initial,index):
    ew=initial[0];tone=ew[BANK-v.E+12*index:BANK-v.E+12*index+12]
    assert memory[v.TRACKS-v.E+0x24:v.TRACKS-v.E+0x30]==tone,'selected instrument differs'
    head=field(memory,v.TRACKS+0x20,4);assert head and field(memory,head)&0x80,'note not created'
    key=field(memory,v.TRACKS+5);kind=tone[0]
    if kind&0xC0:
        child_index=ew[KEYMAP-v.E+key]if kind&0x40 else key
        tone=ew[CHILDREN-v.E+12*child_index:CHILDREN-v.E+12*child_index+12]
        if kind&0x80:key=tone[1]
    assert field(memory,head+1)==tone[0]and field(memory,head+8)==key
    assert field(memory,head+0x24,4)==int.from_bytes(tone[4:8],'little'),'wave pointer not propagated'
    assert field(memory,head+4,4)==int.from_bytes(tone[8:12],'little'),'ADSR not propagated'
    if tone[0]&7:assert field(memory,head+0x1E)==tone[2]
    key+=field(memory,v.TRACKS+8)-(256 if field(memory,v.TRACKS+8)&128 else 0)
    cgb=tone[0]&7;target=0x0810B78C if cgb else 0x0810AC90
    freq_cfg=dict(address=target,native_name='Dbaa_AudioCall',arm_args=[cgb if cgb else field(memory,head+0x24,4),max(key,0),field(memory,v.TRACKS+9)],
        native_args=[],cover_start=target,cover_end=target+180,compare_return=True)
    frequency=v.execute(pt.second_ram(memory,initial),routine=freq_cfg)[2]
    assert field(memory,head+0x20,4)==frequency,'instrument frequency differs from independent ROM call'
    return head


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_voice_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=updates=0
    for ordinal,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
            assert original==native,'RAM, ordered reads or callbacks differ'
            assert START in v.COVERAGE,'VOICE not reached'
            if route.startswith('player_'):
                head=check_note(original[0],ram,cfg['parameter']);players+=1;updates+=1
                assert field(original[0],v.TRACKS+0x40,4)==v.COMMANDS+6
                if cfg['switch']:
                    original2=v.execute(pt.second_ram(original[0],ram),routine=cfg)
                    native2=v.execute(pt.second_ram(native[0],ram),True,routine=cfg)
                    assert original2==native2,'second player update differs'
                    new_head=check_note(original2[0],ram,(cfg['parameter']+1)&255)
                    assert new_head!=head and field(original2[0],new_head+0x34,4)==head
                    # VOICE affects subsequent notes; an already sounding channel keeps its wave and ADSR.
                    for off,width in [(1,1),(4,4),(8,1),(0x20,4),(0x24,4)]:
                        assert field(original2[0],head+off,width)==field(original[0],head+off,width)
                    assert field(original2[0],v.TRACKS+0x40,4)==v.COMMANDS+12
                    results.update(original2[0]);updates+=1
            assert not v.FALLBACK_TARGETS,'unexpected ARM fallback'
        except Exception as exc:
            failure=dict(route=route,seed=seed,index=ordinal,error=repr(exc))
            if original and native:failure.update(rom_trace=original[1],native_trace=native[1],
                ram_offsets=[i for i,(a,b)in enumerate(zip(original[0],native[0]))if a!=b][:32])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',route,seed,repr(exc),flush=True);return 1
        counts[route]=counts.get(route,0)+1;coverage.update(v.COVERAGE&EXPECTED);results.update(original[0])
        if ordinal%256==0:print('Passed voice cases:',ordinal+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==20
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,original_instructions_covered=len(coverage),
        original_instruction_addresses=[hex(a)for a in sorted(coverage)],instrument_bytes_tested=256,status_bytes_tested=256,
        real_player_cases=players,real_player_updates=updates,real_commands_reached_in_every_player_case=True,
        instrument_stride_bytes=12,parameter_read_is_raw=True,filter_uses_record_base_for_all_words=True,
        sequential_read_store_aliases_verified=True,pcm_cgb_wave_adsr_verified=True,
        grouped_rhythm_voices_verified=True,existing_notes_preserved_on_instrument_switch=True,
        frequency_compared_to_independent_rom_call=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),player_sequence_tool_sha256=sha(ROOT/'tools/verify_music_priority_tempo.py'),
        field_tool_sha256=sha(ROOT/'tools/verify_music_key_shift.py'),native_dll_sha256=sha(v.OUT/'music_player_native.dll'),
        compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),results_sha256=results.hexdigest(),
        byte_matching=False,full_game_boot=False,cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'instrument cases;',len(coverage),'instructions;',players,'player sequences',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
