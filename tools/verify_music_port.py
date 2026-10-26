"""Compare PORT native C with the ROM, observing ordered byte writes to a flat I/O mirror."""
from pathlib import Path
from functools import lru_cache
import argparse,ctypes,hashlib,json,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_music_end_tie as held
import verify_music_priority_tempo as pt
ROOT=Path(__file__).resolve().parents[1]
START,INNER=0x0810A6C0,0x0810A54A
IO,IO_SIZE,PORT_BASE=0x04000000,0x400,0x04000060
RAM_SIZE=0x47800
WRITE_WATCH=[v.TRACKS+0x40,*range(IO,IO+IO_SIZE)]
EXPECTED={i.address for i in Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(v.ROM[0x10A6C0:0x10A6D4],START)}


@lru_cache(maxsize=512)
def base_fixture(seed):
    # Immutable deterministic input; cases always copy it before mutation.
    return v.fixture(seed)


def initial(seed):
    ew,iw=map(bytearray,base_fixture(seed%512))
    image=bytearray((i*29+seed)&255 for i in range(IO_SIZE))
    return ew,iw,image


def command_case(seed,index,value,status=0x80,source=None,kind='ram'):
    ew,iw,image=initial(seed);ew[v.TRACKS-v.E]=status
    source=v.COMMANDS if source is None else source
    extras=[]
    if kind=='low':
        source=0x01000000+seed%16;extras=[(source,bytes([index,value]))]
    elif kind=='rom':pass
    elif kind=='boundary_low':
        source=0x01FFFFFF;extras=[(source,bytes([index]))];ew[0]=value
    elif kind=='boundary_wrap':
        source=0xFFFFFFFF;extras=[(source,bytes([index])),(0,bytes([value]))]
    else:
        target,offset=(ew,source-v.E)if v.E<=source<v.E+0x40000 else(iw,source-v.I)if v.I<=source<v.I+0x8000 else(image,source-IO)
        target[offset:offset+2]=bytes([index,value])
    v.w32(ew,v.TRACKS-v.E+0x40,source)
    cfg=dict(address=START,native_name='Dbaa_AudioCall',arm_args=[v.PLAYER,v.TRACKS],
        native_args=[START|(seed&1),v.PLAYER,v.TRACKS,0],cover_start=INNER,cover_end=START+20,
        observe_reads=[v.TRACKS+0x40,source,(source+1)&0xFFFFFFFF],observe_writes=WRITE_WATCH,
        extra_memory=[(IO,bytes(image)),*extras])
    return [ew,iw],cfg


def variants(cases):
    for seed,(index,value,status,kind)in enumerate([(0,255,0x80,'ram'),(255,1,0,'ram'),
        (128,128,0xF3,'ram'),(250,255,0x80,'low'),(0,0,0xFF,'ram')]):
        ram,cfg=command_case(seed,index,value,status,kind=kind);yield 'guards',seed,ram,cfg
    for index in range(256):
        for value in [0,1,128,255]:
            ram,cfg=command_case(index,index,value);yield 'selectors',index*256+value,ram,cfg
    for value in range(256):
        for index in [0,2,4,0x22]:
            ram,cfg=command_case(value,index,value);yield 'parameters',value*256+index,ram,cfg
    for status in range(256):
        ram,cfg=command_case(status,status,(status*73)&255,status);yield 'status_bytes',status,ram,cfg
    for offset in [0,0x16,0x18,0x24,0x28,0x40,0x41,0x42,0x43,0x44,0x4F,0x50]:
        for value in [0,1,127,128,254,255]:
            ram,cfg=command_case(offset+value,(value*17)&255,value,0x83,v.TRACKS+offset)
            yield 'aliases',offset*256+value,ram,cfg
    for seed in range(16):
        for route,source,kind in [('filtered_sources',None,'low'),('io_sources',IO+0x60+(seed*11)%256,'ram'),
            ('iwram_sources',v.I+0x6000+seed*4,'ram'),('rom_sources',0x080000C0+seed*2,'rom')]:
            ram,cfg=command_case(seed,255-seed,(seed*17)&255,source=source,kind=kind);yield route,seed,ram,cfg
    for seed,kind in enumerate(['boundary_low','boundary_wrap']):
        ram,cfg=command_case(seed,255,0xEE,kind=kind);yield 'boundary_sources',seed,ram,cfg
    rng=random.Random(0xA6C0CC)
    for seed in range(cases):
        ram,cfg=command_case(seed,rng.randrange(256),rng.randrange(256),rng.randrange(256));yield 'random',seed,ram,cfg
    fixtures=[ram for route,seed,ram,cfg in held.variants(0)if route=='player_held_note']
    for index in range(256):
        for live in [False,True]:
            ew,iw=map(bytearray,fixtures[(index+int(live))%64]);t=v.TRACKS-v.E;p=v.PLAYER-v.E
            ew[t]=0x8F;ew[t+0x17]=ew[t+0x19]=ew[t+0x1B]=0
            v.w16(ew,p+0x20,150);v.w32(ew,p+12,0)
            v.w32(iw,v.TABLE-v.I+27*4,START+1)
            a,b=(index*37+1)&255,(index*73+128)&255
            ports=[0xCC,index,a,0xCC,index,b]
            stream=([0xCF,60,100,0x81,*ports,0x81]if live else[*ports,0xCF,60,100,0x81,0x81])
            ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)]=bytes(stream)
            cfg=dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',arm_args=[v.PLAYER],native_args=[v.PLAYER],
                cover_start=INNER,cover_end=START+20,observe_reads=[v.TRACKS+0x40,*range(v.COMMANDS,v.COMMANDS+16)],
                observe_writes=WRITE_WATCH,extra_memory=[(IO,bytes((n*29+index)&255 for n in range(IO_SIZE)))],
                port=index,values=[a,b],live=live)
            yield 'player_live'if live else'player_create',index,[ew,iw],cfg


def field(memory,address,width=1):
    off=address-v.E if address<v.I else 0x40000+address-v.I
    return int.from_bytes(memory[off:off+width],'little')


def expected_command(ram,cfg):
    source=v.u32(ram[0],v.TRACKS-v.E+0x40);cursor=(source+2)&0xFFFFFFFF
    def read(address,updated=False):
        if updated and v.TRACKS+0x40<=address<v.TRACKS+0x44:
            return (cursor>>(8*(address-v.TRACKS-0x40)))&255
        if v.E<=address<v.E+0x40000:return ram[0][address-v.E]
        if v.I<=address<v.I+0x8000:return ram[1][address-v.I]
        if 0x08000000<=address<0x09000000:return v.ROM[address-0x08000000]
        for base,data in cfg['extra_memory']:
            if base<=address<base+len(data):return data[address-base]
        raise AssertionError(('unmapped oracle input',hex(address)))
    index=read(source);payload=(source+1)&0xFFFFFFFF;raw=read(payload,True)
    template=struct.unpack_from('<I',v.ROM,0x10A544)[0]
    value=0 if not(payload>>25)and(payload<template or payload>>14)else raw
    trace=[('read',v.TRACKS+0x40,4),('read',source,1),('write',v.TRACKS+0x40,4,cursor),
        ('read',payload,1),('write',PORT_BASE+index,1,value)]
    return cursor,index,value,trace


def io_writes(trace):return [row for row in trace if row[0]=='write'and IO<=row[1]<IO+IO_SIZE]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_music_port_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.NATIVE=v.build_native()
    counts={};coverage=set();results=hashlib.sha256();players=updates=writes=0
    for number,(route,seed,ram,cfg)in enumerate(variants(args.cases)):
        original=native=None
        try:
            v.COVERAGE.clear();v.FALLBACK_TARGETS.clear()
            original=v.execute(ram,routine=cfg);native=v.execute(ram,True,routine=cfg)
            assert original==native,'RAM, I/O image or ordered reads/writes differ'
            if route.startswith('player_'):
                first=original[0];head=field(first,v.TRACKS+0x20,4)
                assert head and field(first,head)&0x80 and field(first,head+8)==60
                cfg2=dict(cfg,extra_memory=[(IO,first[RAM_SIZE:RAM_SIZE+IO_SIZE])])
                original2=v.execute(pt.second_ram(first[:RAM_SIZE],ram),routine=cfg2)
                native2=v.execute(pt.second_ram(native[0][:RAM_SIZE],ram),True,routine=cfg2)
                assert original2==native2,'second player update differs'
                second=original2[0];target=PORT_BASE+cfg['port']
                expected_writes=[('write',target,1,value)for value in cfg['values']]
                assert io_writes(original[1])+io_writes(original2[1])==expected_writes,'PORT writes were missing, merged or reordered'
                assert io_writes(original[1])==([]if cfg['live']else expected_writes)
                assert io_writes(original2[1])==(expected_writes if cfg['live']else[])
                assert field(second,v.TRACKS+0x20,4)==head and field(second,v.PLAYER+12,4)==2
                assert field(second,v.TRACKS+0x40,4)==v.COMMANDS+11
                if cfg['live']:
                    for off in range(64):assert field(second,head+off)==field(first,head+off),'PORT changed note software state'
                image=bytearray(cfg['extra_memory'][0][1]);image[target-IO]=cfg['values'][-1]
                assert second[RAM_SIZE:RAM_SIZE+IO_SIZE]==bytes(image),'PORT touched adjacent I/O bytes'
                writes+=2;players+=1;updates+=2;results.update(second)
            else:
                cursor,index,value,trace=expected_command(ram,cfg)
                assert original[1]==trace,'independent bus/cursor trace differs'
                assert field(original[0],v.TRACKS+0x40,4)==cursor
                image=bytearray(cfg['extra_memory'][0][1]);image[PORT_BASE+index-IO]=value
                assert original[0][RAM_SIZE:RAM_SIZE+IO_SIZE]==bytes(image),'independent I/O image differs'
                writes+=1
            assert {START,INNER}<=v.COVERAGE and 0x0810A548 not in v.COVERAGE,'wrong filtered-reader entry'
            assert not v.FALLBACK_TARGETS,'unexpected ARM fallback'
            error=None
        except Exception as exc:error=repr(exc)
        if error:
            failure=dict(route=route,seed=seed,index=number,error=error)
            if original and native:failure.update(rom_trace=original[1],native_trace=native[1],ram_offsets=[i for i,(a,b)in enumerate(zip(original[0],native[0]))if a!=b][:32])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n');print('FAIL:',route,seed,error,flush=True);return 1
        counts[route]=counts.get(route,0)+1;coverage.update(v.COVERAGE&EXPECTED);results.update(original[0])
        if number%256==0:print('Passed PORT cases:',number+1,flush=True)
    assert coverage==EXPECTED and len(EXPECTED)==9
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,rom_sha1=expected,
        all_ram_equal=True,io_images_equal=True,ordered_reads_and_writes_equal=True,callback_traces_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        selector_bytes_tested=256,parameter_bytes_tested=256,status_bytes_tested=256,real_player_cases=players,real_player_updates=updates,
        observed_port_writes=writes,real_commands_reached_in_every_player_case=True,raw_selector_and_filtered_value_verified=True,
        interior_reader_entry_verified=True,cursor_two_byte_advance_and_wrap_verified=True,cursor_before_value_read_verified=True,
        io_byte_width_address_order_and_no_duplicates_verified=True,register_aliases_and_adjacent_bytes_verified=True,
        live_note_software_state_preserved=True,io_mirror_carried_between_updates=True,
        io_model='flat 0x04000000..0x040003FF mirror plus bus trace; device side effects are not emulated',
        hardware_register_side_effects_validated=False,audible_output_validated=False,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        held_fixture_tool_sha256=sha(ROOT/'tools/verify_music_end_tie.py'),player_sequence_tool_sha256=sha(ROOT/'tools/verify_music_priority_tempo.py'),
        native_dll_sha256=sha(v.OUT/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        results_sha256=results.hexdigest(),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional comparison, not GBA cycles or full hardware')
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'PORT cases;',writes,'byte writes;',updates,'player updates;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
