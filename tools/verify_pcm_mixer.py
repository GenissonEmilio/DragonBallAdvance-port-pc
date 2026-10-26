"""ROM-versus-native PCM mixer, including relocated Thumb/ARM execution.

Compare observable RAM, ordered data bus access and raw PCM bytes. A separate
scalar oracle checks isolated nominal-envelope voices; it does not model cycles.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_ARM
import verify_music_player as v
import verify_sound_frequency as f
import verify_sound_initialization as init

ROOT=Path(__file__).resolve().parents[1]
ENTRY,RAM,SOURCE,COPY=0x0810A084,0x030008B0,0x0810A108,1024
SOUND,PLAYER,TRACK,WAVES=0x03000CC0,v.E+0x100,v.E+0x3000,v.E+0x10000
RANGES=[(0x0810A084,0x0810A0EE,CS_MODE_THUMB),(0x0810A108,0x0810A112,CS_MODE_THUMB),
    (0x0810A114,0x0810A168,CS_MODE_ARM),(0x0810A168,0x0810A1BA,CS_MODE_THUMB),
    (0x0810A1C0,0x0810A29E,CS_MODE_THUMB),(0x0810A2A0,0x0810A488,CS_MODE_ARM),
    (0x0810A488,0x0810A4A8,CS_MODE_THUMB)]
EXPECTED={i.address for a,b,mode in RANGES for i in Cs(CS_ARCH_ARM,mode).disasm(v.ROM[a-0x08000000:b-0x08000000],a)}
LOCKS=[0,1,f.MAGIC-1,f.MAGIC,f.MAGIC+1,f.MAGIC+10,0xFFFFFFFF]
BASE_WATCH=init.watched
def watched(a,n):
    if RAM<=a<RAM+COPY:return False
    return BASE_WATCH(a,n)or 0x08A676D4<=a<0x08A67784 or 0x08800000<=a<0x08801000


def case(route,seed,**kw):
    result=dict(route=route,seed=seed,target=ENTRY,mode=0,sound=SOUND,lock=f.MAGIC,clock=[],
        ram_code_map=[RAM,SOURCE,COPY],frames=32,voices=1,status=1,kind=8,envelope=255,
        master=15,right=255,left=128,attack=64,decay=192,sustain=128,release=128,echo=16,
        echo_length=3,length=64,loop_start=3,loop=False,fraction=0,step=0x800000,
        reciprocal=1,reverb=0,dma=1,fields={},player=False,cgb=False)
    result.update(kw);return result


def variants(count):
    guards=[dict(lock=0),dict(status=0),dict(status=0xC0),dict(status=0x80),dict(kind=0),
        dict(loop=True,length=7,loop_start=3),dict(kind=0,step=0x1800000,length=5,loop=True),
        dict(status=0x44,echo_length=0),dict(status=0x40,envelope=1,echo=0),
        dict(reverb=127),dict(frames=224,dma=2),dict(player=True,cgb=True,voices=2)]
    for seed,kw in enumerate(guards):yield case('guards',seed,**kw)
    for flag in [0,0x3F,0x40,0x80,0xC0,0xFF]:
        yield case('guards',flag+100,status=0x80,loop=True,wave_flags=flag)
    for lock in LOCKS:yield case('locks',lock,lock=lock)
    for frames in [0,1,2,3,4,5,7,8,12,15,16,17,28,31,96,132,176,224,264,304,352,448,528,608,672,704]:
        for kind in [0,8]:yield case('frame_sizes',frames+kind,frames=frames,kind=kind,voices=2,loop=True,length=31)
    for status in range(256):
        for kind in [0,8]:yield case('status_bytes',status*2+kind,status=status,kind=kind)
    for field in ['attack','decay','sustain','release','echo','echo_length','envelope','master','right','left','reverb']:
        for value in [0,1,2,3,7,15,16,31,63,127,128,129,192,254,255]:
            yield case('envelope_and_gain',value,**{field:value},status=0x80 if field=='attack'else 2 if field in ['decay','sustain']else 0x40 if field in ['release','echo']else 4 if field=='echo_length'else 1)
    for length in range(1,41):
        for kind in [0,8]:
            for loop in [False,True]:
                yield case('sample_ends',length*4+kind,kind=kind,length=length,loop=loop,loop_start=length//2,
                    step=[0,0x400000,0x800000,0x1800000][length%4])
    for frames in [96,132,176,224,264,304,352,448,528,608,672,704]:
        for dma in [0,1,2,3]:
            yield case('dma_ring',frames+dma,frames=frames,dma=dma,voices=0,reverb=31)
    for voices in range(13):
        for kind in [0,8]:yield case('polyphony',voices*2+kind,voices=voices,kind=kind,frames=96,loop=True,length=127)
    for value in range(256):yield case('reverb_bytes',value,reverb=value,voices=0)
    for line in range(256):
        maximum=1+(line%5);deadline=maximum+(line+228 if line<160 else line)
        lines=[line];polls=[(line+i+1)&255 for i in range(4)]
        for sample in polls:
            lines.append(sample)
            if(sample+228 if sample<160 else sample)>=deadline:break
        yield case('line_deadlines',line,voices=4,clock=lines,max_lines=maximum)
    for seed in range(24):
        yield case('lifecycle',seed,voices=2,frames=96,kind=seed%2*8,loop=True,length=13,player=bool(seed&2),cgb=bool(seed&4))
    for frames in [16,28,96]:
        for kind in [0,8]:
            for step in [0,1,0x400000,0x800000,0x1800000,0x3F000000]:
                for loop in [False,True]:
                    yield case('scalar_pcm',frames+kind+step,frames=frames,kind=kind,step=step,loop=loop,length=43,loop_start=7,
                        fraction=0x123456,reverb=(frames%3)*31)
    for seed in range(32):yield case('player_cgb',seed,player=True,cgb=True,voices=2,loop=bool(seed&1),frames=96,kind=(seed%2)*8)
    rng=random.Random(0xA084A108)
    for seed in range(count):
        length=rng.randrange(1,256);frames=rng.choice([16,28,96,132,224,264])
        yield case('random',seed,frames=frames,voices=rng.randrange(5),status=rng.randrange(256),kind=rng.choice([0,8]),
            length=length,loop_start=rng.randrange(length),loop=bool(seed&1),fraction=rng.randrange(0x800000),
            step=rng.choice([0,0x12345,0x400000,0x800000,0x1800000,0xC000000]),reverb=rng.randrange(256),
            master=rng.randrange(256),right=rng.randrange(256),left=rng.randrange(256),envelope=rng.randrange(256),
            attack=rng.randrange(256),decay=rng.randrange(256),sustain=rng.randrange(256),release=rng.randrange(256),
            echo=rng.randrange(256),echo_length=rng.randrange(256),dma=rng.choice([0,1,2]))


def region(images,a,n):
    for base,data in [(v.E,images[0]),(v.I,images[1]),(f.IO,images[2]),(0x08000000,v.ROM)]:
        if base<=a and a+n<=base+len(data):return data,a-base
    raise AssertionError(('unmapped fixture',hex(a),n))
def get(images,a,n=1):
    data,offset=region(images,a,n);return int.from_bytes(data[offset:offset+n],'little')
def put(images,a,value,n=1):
    data,offset=region(images,a,n);data[offset:offset+n]=(value&((1<<(8*n))-1)).to_bytes(n,'little')


def initial(cfg):
    images=[bytearray(x)for x in f.initial(cfg)]
    images[1][RAM-v.I:RAM-v.I+COPY]=v.ROM[SOURCE-0x08000000:SOURCE-0x08000000+COPY]
    p=cfg['sound']
    for off in range(0x350):put(images,p+off,0)
    values={0:(cfg['lock'],4),4:(cfg['dma'],1),5:(cfg['reverb'],1),6:(cfg['voices'],1),7:(cfg['master'],1),
        11:(1584//max(cfg['frames'],1),1),12:(cfg.get('max_lines',0),1),16:(cfg['frames'],4),24:(cfg['reciprocal'],4),
        28:(v.E+0x4000,4),32:(0x0810A725 if cfg['player']else 0,4),36:(PLAYER,4),
        40:(0x0810B8ED if cfg['cgb']else 0x0810C225,4),44:(0x0810B835,4),48:(0x0810B78D,4),
        52:(0x03001C70,4),56:(0x0810AA01,4)}
    for off,(value,width)in values.items():put(images,p+off,value,width)
    table=list(struct.unpack_from('<36I',v.ROM,0xA67460))
    for index,pointer in init.PATCHES:table[index]=pointer
    for index,value in enumerate(table):put(images,0x03001C70+4*index,value,4)
    for voice in range(max(1,cfg['voices'])):
        ch=p+80+voice*64;wave=WAVES+voice*0x1000
        fields={0:cfg['status']if cfg['voices']else 0,1:cfg['kind'],2:cfg['right'],3:cfg['left'],4:cfg['attack'],
            5:cfg['decay'],6:cfg['sustain'],7:cfg['release'],9:cfg['envelope'],12:cfg['echo'],13:cfg['echo_length']}
        fields.update(cfg['fields'])
        for off,value in fields.items():put(images,ch+off,value)
        for off,value in [(24,cfg['length']),(28,cfg['fraction']),(32,cfg['step']),(36,wave),(40,wave+16)]:put(images,ch+off,value,4)
        # A continuing voice needs the loop status bit already set.
        if cfg['loop']and not(cfg['status']&128):put(images,ch,cfg['status']|16)
        put(images,wave+3,cfg.get('wave_flags',0xC0 if cfg['loop']else 0));put(images,wave+8,cfg['loop_start'],4);put(images,wave+12,cfg['length'],4)
        for off in range(2048):put(images,wave+16+off,(off*73+cfg['seed']*19+voice*37)&255)
    for index in range(4):
        ch=v.E+0x4000+64*index
        for off in range(64):put(images,ch+off,0)
        for off,value in {1:index+1,2:120,3:80,4:2,5:2,6:128,7:2,12:128,13:3,28:0x11<<index,30:16,31:8}.items():put(images,ch+off,value)
        if index==0 and cfg['cgb']:put(images,ch,0x80)
    if cfg['player']:
        for index in range(2):
            player=PLAYER+index*0x100;track=TRACK+index*80;stream=v.E+0x8000+index*128
            for off in range(64):put(images,player+off,0)
            for off in range(80):put(images,track+off,0)
            for off,value,width in [(4,0,4),(8,1,1),(32,150,2),(44,track,4),(52,f.MAGIC,4),
                (56,0x0810A725 if index==0 else 0,4),(60,PLAYER+0x100,4)]:put(images,player+off,value,width)
            put(images,track,0x80);put(images,track+1,1);put(images,track+64,stream,4)
            for off in range(20):put(images,stream+off,0x81 if off<8 else 0xB1)
            if index<cfg['voices']:
                ch=p+80+index*64;put(images,track+32,ch,4);put(images,ch+44,track,4);put(images,ch+52,0,4)
    return[bytes(x)for x in images]


def s8(value):return value-256 if value&128 else value
def signed(value):return(value&0xFFFFFFFF)-0x100000000 if value&0x80000000 else value&0xFFFFFFFF


def scalar_pcm(cfg,images):
    """Independent per-sample math, for one continuing sustain voice only."""
    p=cfg['sound'];out=p+0x350;n=cfg['frames'];wanted=[bytearray(x)for x in images]
    reverb=cfg['reverb']
    if reverb:
        for i in range(n):
            total=sum(s8(get(wanted,a))for a in [out+i+0x630,out+i,out+n+i+0x630,out+n+i])
            value=total*reverb//512
            if value&128:value+=1
            put(wanted,out+i+0x630,value);put(wanted,out+i,value)
    else:
        for i in range(n):put(wanted,out+i,0);put(wanted,out+i+0x630,0)
    ch=p+80;wave=get(images,ch+36,4);cursor=get(images,ch+40,4);count=cfg['length'];fraction=cfg['fraction']
    gain=(cfg['master']+1)*cfg['envelope']//16
    gains=[(cfg['right']*gain//256)&255,(cfg['left']*gain//256)&255]
    remaining=cfg['length']-cfg['loop_start'];loopbase=wave+16+cfg['loop_start']
    a=s8(get(images,cursor));b=s8(get(images,cursor+1))
    for index in range(n):
        sample=a if cfg['kind']&8 else signed((a+signed((fraction*(b-a))&0xFFFFFFFF)//(1<<23))&0xFFFFFFFF)
        for side,volume in enumerate(gains):
            address=out+index+side*0x630;put(wanted,address,get(wanted,address)+sample*volume//256)
        if cfg['kind']&8:
            cursor+=1;count-=1
            if count==0:
                if not cfg['loop']:break
                count=remaining;cursor=loopbase
            a=s8(get(images,cursor))
        else:
            fraction=(fraction+cfg['step'])&0xFFFFFFFF;advance=fraction>>23
            if advance:
                fraction&=~0x3F800000;count-=advance
                if count<=0:
                    if not cfg['loop']:break
                    offset=-count
                    while count<=0:count+=remaining;offset-=remaining if count<=0 else 0
                    cursor=loopbase+offset
                else:cursor+=advance
                a=s8(get(images,cursor));b=s8(get(images,cursor+1))
    return bytes(wanted[1][out-v.I:out-v.I+n]),bytes(wanted[1][out-v.I+0x630:out-v.I+0x630+n])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=256);parser.add_argument('--sample-step',type=int,default=1)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_pcm_mixer_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    parser.add_argument('--mixer-source',type=Path)
    parser.add_argument('--player-source',type=Path,default=v.HOST_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0 or args.sample_step<1:parser.error('invalid sampling')
    assert hashlib.sha1(v.ROM).hexdigest()==json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    v.OUT=out;v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();v.HOST_SOURCE=args.player_source.resolve()
    if args.mixer_source:
        source=v.HOST_HELPERS_SOURCE.read_text()
        assert source.count('#include "pcm_mixer_impl.h"')==1
        changed=out/'audio_helpers_variant.c'
        changed.write_text(source.replace('#include "pcm_mixer_impl.h"',f'#include "{args.mixer_source.resolve().as_posix()}"'))
        v.HOST_HELPERS_SOURCE=changed
    dll=v.build_native()
    f.watched=watched;f.EXPECTED=EXPECTED
    counts={};coverage=set();digest=hashlib.sha256();executions=scalar_checks=cycles=io_writes=0
    for index,cfg in enumerate(variants(args.cases)):
        if cfg['route']not in ['guards','lifecycle','player_cgb']and index%args.sample_step:continue
        images=initial(cfg);steps=24 if cfg['route']=='lifecycle'else 1
        rom_trace=native_trace=None
        try:
            expected_pcm=scalar_pcm(cfg,images)if cfg['route']=='scalar_pcm'else None
            for frame in range(steps):
                original,rom_trace,reads=f.execute(cfg,images,None,out,coverage)
                native,native_trace,nreads=f.execute(cfg,images,dll,out,coverage)
                assert f.comparable(original)==f.comparable(native),'RAM or PCM differs'
                assert rom_trace==native_trace,'ordered bus trace differs'
                assert reads==nreads,'global pointer reads differ'
                if expected_pcm:
                    p=cfg['sound']+0x350;n=cfg['frames']
                    assert tuple(bytes(region(original,p+side*0x630,n)[0][region(original,p+side*0x630,n)[1]:region(original,p+side*0x630,n)[1]+n])for side in range(2))==expected_pcm,'scalar PCM differs'
                    scalar_checks+=1
                executions+=1;cycles+=int(steps>1)
                io_writes+=sum(row[0]=='write'and f.IO<=row[1]<f.IO+1024 for row in rom_trace)
                digest.update(f.comparable(original));digest.update(json.dumps(rom_trace).encode())
                original[1]=original[1][:0x7000]+images[1][0x7000:0x7800]+original[1][0x7800:];images=original
        except Exception as exc:
            (out/'failed_case.json').write_text(json.dumps(dict(case=cfg,error=repr(exc),rom_trace=rom_trace,native_trace=native_trace),indent=2)+'\n')
            print('FAIL:',cfg['route'],cfg['seed'],repr(exc),flush=True);return 1
        counts[cfg['route']]=counts.get(cfg['route'],0)+1
        if sum(counts.values())%128==1:print('Passed PCM mixer cases:',sum(counts.values()),flush=True)
    missing=EXPECTED-coverage
    if args.sample_step==1:assert not missing,[hex(a)for a in sorted(missing)]
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),executions=executions,routes=counts,random_cases=args.cases,sample_step=args.sample_step,
        scalar_pcm_cases=scalar_checks,lifecycle_sequences=counts.get('lifecycle',0),lifecycle_updates=cycles,
        mixer_instructions_covered=len(coverage),mixer_instruction_count=len(EXPECTED),mixer_instruction_addresses=[hex(a)for a in sorted(coverage)],
        missing_mixer_instructions=[hex(a)for a in sorted(missing)],copied_ram_bytes=COPY,relocated_code_executed=True,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_mixer_fallback_to_arm=False,
        all_ram_equal=True,raw_pcm_bytes_equal=True,ordered_reads_and_writes_equal=True,observed_io_writes=io_writes,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),frequency_tool_sha256=sha(ROOT/'tools/verify_sound_frequency.py'),
        native_dll_sha256=sha(out/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        rom_sha1=hashlib.sha1(v.ROM).hexdigest(),results_sha256=digest.hexdigest(),byte_matching=False,full_game_boot=False,
        hardware_register_side_effects_validated=False,real_time_validated=False,audible_output_validated=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'PCM mixer cases;',executions,'executions;',len(coverage),'instructions; missing',len(missing),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
