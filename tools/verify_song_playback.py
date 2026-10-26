"""Original ROM song APIs and PCM versus native C, with no native ARM fallback.

The ROM oracle executes original instructions in Unicorn. It models the already
documented flat audio I/O, not the analog DAC or a full GBA/game boot.
"""
from pathlib import Path
import argparse,array,bisect,ctypes,hashlib,json,random,struct,wave
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import build_windows_audio as build
import verify_music_player as v
import verify_sound_frequency as f
import verify_sound_mode as mode
import verify_audio_startup as startup
import verify_pcm_mixer as mixer
import verify_windows_audio as windows

ROOT=Path(__file__).resolve().parents[1]
START_SONG,START,STOP,STOP_ALL=0x0810ADB8,0x0810B4EC,0x0810B5D0,0x0810AEEC
SONGS,PLAYERS,EMPTY=0x08A69068,0x08A69038,0x08A6AEB8
SONG_COUNT=(EMPTY-SONGS)//8
RANGES=[(START_SONG,0x0810ADDC),(STOP_ALL,0x0810AF10),
        (START,0x0810B5CC),(STOP,0x0810B60C)]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
NEW_CODE={i.address for a,b in RANGES for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}


def watched(a,n):
    # The copied mixer's literal/code bytes and dead CPU stack have no native
    # instruction counterpart. All actual song, sample and instrument reads
    # are observed, along with every persistent RAM and audio I/O access.
    if mixer.RAM<=a<mixer.RAM+mixer.COPY:return False
    return(v.E<=a<v.E+0x40000 or v.I<=a<v.I+0x8000 and not v.I+0x7000<=a<v.I+0x7800
           or f.IO<=a<f.IO+1024 or 0x08A67460<=a<0x09000000)


def catalog():
    result=[]
    for i in range(SONG_COUNT):
        header,player,unknown=struct.unpack_from('<IHH',v.ROM,SONGS-0x08000000+i*8)
        assert 0x08000000<=header<0x09000000 and player<4
        count,blocks,priority,sound_mode,voice=struct.unpack_from('<BBBBI',v.ROM,header-0x08000000)
        assert count<=16
        tracks=list(struct.unpack_from('<'+'I'*count,v.ROM,header-0x08000000+8))
        assert all(0x08000000<=p<0x09000000 for p in tracks)
        result.append(dict(id=i,header=header,player=player,tracks=count,blocks=blocks,
                           priority=priority,mode=sound_mode,voicegroup=voice,track_pointers=tracks))
    assert min(x['header']for x in result)==EMPTY and SONG_COUNT==970
    return result


def bind(rt):
    for name,args in [('StartSong',[ctypes.c_uint]),('StopPlayer',[ctypes.c_uint]),('StopAll',[])]:
        fn=getattr(rt.dll,'Dbaa_AudioRuntime'+name)
        fn.argtypes=[ctypes.c_void_p,*args];fn.restype=ctypes.c_int;setattr(rt,name,fn)


def api_cases(quick=False):
    p,t,h,c=v.E+0x1000,v.E+0x4000,v.E+0x2000,v.E+0x18000
    def case(route,**kw):
        cfg=dict(route=route,seed=0,target=START,mode=p,a1=h,clock=[],capacity=3,count=2,
                 lock=f.MAGIC,check=0,old_song=h,first_status=0x80,status=1,
                 held_priority=127,priority=64,song_mode=0x80,channels=True)
        cfg.update(kw);return cfg
    for lock in [0,f.MAGIC,f.MAGIC+1,0xFFFFFFFF]:
        for target in [START,STOP]:yield case('locks',lock=lock,target=target)
    for capacity in ([0,1,3]if quick else[0,1,2,16,255]):
        for count in ([0,2,4]if quick else[0,1,2,16,255]):
            yield case('track_limits',capacity=capacity,count=count)
    for old,first,status in [(0,0,0),(h,0x40,0),(h,0,1),(h,0,0x80000001),(h,0,0x10000)]:
        for priority in ([63,127,255]if quick else range(256)):
            yield case('priority',check=1,old_song=old,first_status=first,status=status,priority=priority)
    for value in ([0,128,255]if quick else range(256)):
        yield case('mode_bytes',song_mode=value,channels=False)
    for count in ([0,3]if quick else range(256)):
        yield case('stop_count_bytes',target=STOP,capacity=count)
    for mod_type in ([0,1,2]if quick else[0,1,2,255]):
        for channel_type in ([0,1]if quick else range(5)):
            for phase in ([0,250]if quick else[0,64,128,250]):
                yield case('player_lfo_bus',target=0x0810A724,mod_type=mod_type,channel_type=channel_type,phase=phase)
    for i in ([0,1,6,13,969]if quick else range(SONG_COUNT)):
        yield case('rom_song_ids',target=START_SONG,mode=i)
    for i in ([1]if quick else[0x10001,0xFFFF0001,0x12340006,0xABC003C9]):
        yield case('song_u16_truncation',target=START_SONG,mode=i)
    yield case('global_stop',target=STOP_ALL)


def api_images(base,cfg):
    images=[bytearray(x)for x in base]
    p,t,h,c=v.E+0x1000,v.E+0x4000,v.E+0x2000,v.E+0x18000
    put=lambda a,x,n=1:mixer.put(images,a,x,n)
    if cfg['target']==0x0810A724:
        for a,x,n in [(p+0x34,f.MAGIC,4),(p+4,0,4),(p+8,1,1),(p+0x2C,t,4),(p+0x20,150,2),
                      (t,0x80,1),(t+1,1,1),(t+0x20,c,4),(t+0x17,5,1),(t+0x19,22,1),
                      (t+0x18,cfg['mod_type'],1),(t+0x1A,cfg['phase'],1),(t+0x12,100,1),
                      (t+0x13,64,1),(c,1,1),(c+1,cfg['channel_type'],1),(c+8,60,1),
                      (c+0x12,100,1),(c+0x2C,t,4),(c+0x24,v.E+0x10000,4),(v.E+0x10004,0x400000,4)]:
            put(a,x,n)
    elif cfg['target']in[START,STOP]:
        for a,x,n in [(p+0x34,cfg['lock'],4),(p,cfg['old_song'],4),(p+4,cfg['status'],4),
                      (p+8,cfg['capacity'],1),(p+9,cfg['held_priority'],1),(p+11,cfg['check'],1),
                      (p+0x2C,t,4),(h,cfg['count'],1),(h+2,cfg['priority'],1),
                      (h+3,cfg['song_mode'],1),(h+4,0x08A67738,4)]:
            put(a,x,n)
        for i in range(max(cfg['capacity'],cfg['count'])):
            track=t+80*i;channel=c+128*i
            put(h+8+4*i,0x08D0E000+4*i,4)
            put(track,cfg['first_status']if not i else[0,0x80,0xC0][i%3])
            put(track+0x20,channel if cfg['channels']else 0,4)
            for j in range(2):
                ch=channel+64*j
                put(ch,[0,1,0x80,0xC7][(i+j)%4]);put(ch+1,(i+j)%5)
                put(ch+0x2C,track,4);put(ch+0x30,ch-64 if j else 0,4)
                put(ch+0x34,ch+64 if not j else 0,4)
    elif cfg['target']==STOP_ALL:
        for i,(player,tracks,count,priority)in enumerate(startup.PLAYERS):
            put(player+4,1,4)
            put(player+0x34,0 if i==1 else f.MAGIC,4)
            for j in range(count):
                ch=c+(i*16+j)*64;track=tracks+80*j
                put(track,0x80);put(track+0x20,ch,4);put(ch,1);put(ch+1,j%5)
                put(ch+0x2C,track,4);put(ch+0x34,0,4)
    return[bytes(x)for x in images]


class RomEngine:
    """Persistent original-code oracle; no translated/native game code loaded."""
    def __init__(self,images,coverage):
        self.uc=v.Uc(v.UC_ARCH_ARM,v.UC_MODE_THUMB)
        self.uc.ctl_set_cpu_model(v.UC_CPU_ARM_926);self.trace=[];self.coverage=coverage
        for a,n,data in [(0x08000000,0x1000000,v.ROM),(v.E,0x40000,images[0]),
                         (v.I,0x8000,images[1]),(f.IO,4096,images[2])]:
            self.uc.mem_map(a,n);self.uc.mem_write(a,bytes(data))
        def read(machine,access,a,n,value,data):
            if watched(a,n):self.trace.append(('read',a,n,int.from_bytes(machine.mem_read(a,n),'little')))
        def write(machine,access,a,n,value,data):
            if watched(a,n):self.trace.append(('write',a,n,value&((1<<(8*n))-1)))
        def code(machine,a,n,data):
            if a in NEW_CODE:self.coverage.add(a)
        self.uc.hook_add(v.UC_HOOK_MEM_READ,read);self.uc.hook_add(v.UC_HOOK_MEM_WRITE,write)
        for a,b in RANGES:self.uc.hook_add(v.UC_HOOK_CODE,code,begin=a,end=b-1)
    def invoke(self,target,a=0,b=0,c=0):
        saved=[0xA0B00000+i for i in range(8)]
        for reg,value in zip(v.REGS[4:],saved):self.uc.reg_write(reg,value)
        for reg,value in zip(v.REGS[:3],[a,b,c]):self.uc.reg_write(reg,value)
        self.uc.reg_write(v.UC_ARM_REG_SP,v.I+0x7800);self.uc.reg_write(v.UC_ARM_REG_LR,v.STOP+1)
        self.uc.emu_start(target|1,v.STOP,count=1000000)
        assert self.uc.reg_read(v.UC_ARM_REG_PC)==v.STOP,'ROM instruction limit'
        assert self.uc.reg_read(v.UC_ARM_REG_SP)==v.I+0x7800
        assert [self.uc.reg_read(r)for r in v.REGS[4:]]==saved
    def images(self):return[bytes(self.uc.mem_read(a,n))for a,n in[(v.E,0x40000),(v.I,0x8000),(f.IO,1024)]]


def assert_equal(images,other,trace,other_trace,context):
    assert f.comparable(images)==f.comparable(other),context+': persistent RAM/I/O differs'
    if trace!=other_trace:
        at=next((i for i,(a,b)in enumerate(zip(trace,other_trace))if a!=b),min(len(trace),len(other_trace)))
        raise AssertionError((context,'ordered bus differs',at,trace[max(0,at-2):at+4],other_trace[max(0,at-2):at+4]))


def fnv(data):
    value=14695981039346656037
    for x in data:value=((value^x)*1099511628211)&0xFFFFFFFFFFFFFFFF
    return f'{value:016x}'


def run(out,dll,quick,frames,song_id):
    rt=windows.Runtime(dll);bind(rt);coverage=set();counts={};digest=hashlib.sha256()
    rows=catalog();(out/'catalog.json').write_text(json.dumps(rows,indent=2)+'\n')
    try:
        rt.reset();base=rt.images();rt.Observe(rt.r,windows.OBS(),None)
        # Boundary checks are host policy, separate from the ROM's u16 API.
        assert not rt.StartSong(rt.r,970)and not rt.StartSong(rt.r,0x10001)
        assert not rt.StopPlayer(rt.r,4)and rt.stats().faults==0
        f.EXPECTED=NEW_CODE;f.watched=watched
        for number,cfg in enumerate(api_cases(quick)):
            images=api_images(base,cfg)
            original,trace,reads=f.execute(cfg,images,None,out,coverage)
            native,nt,nreads=f.execute(cfg,images,dll,out,set())
            nt=[x for x in nt if watched(x[1],x[2])]
            assert_equal(original,native,trace,nt,cfg['route'])
            assert reads==nreads
            digest.update(f.comparable(original));counts[cfg['route']]=counts.get(cfg['route'],0)+1
            if number%256==0:print('Passed song API cases:',number+1,flush=True)
        assert NEW_CODE<=coverage,('uncovered song API instructions',[hex(a)for a in sorted(NEW_CODE-coverage)])
        rt.reset();rt.filter=watched;rt.Observe(rt.r,rt.observer,None);rt.Gain(rt.r,64)
        original=RomEngine(rt.images(),coverage)
        pcm=bytearray();raw=hashlib.sha256();host_frames=source_samples=0
        # Each action is executed by the real ROM entry as well as native C.
        actions={0:('start',song_id)}
        if quick:
            actions.update({60:('player_stop',rows[song_id]['player']),64:('start',song_id),
                            72:('global_stop',0)})
        else:
            actions.update({frames//3:('player_stop',rows[song_id]['player']),
                            frames//3+8:('start',song_id),frames-8:('global_stop',0)})
        for frame in range(frames):
            original.trace=[];rt.trace=[]
            if frame in actions:
                action,value=actions[frame]
                if action=='start':
                    assert rt.StartSong(rt.r,value);original.invoke(START_SONG,value)
                elif action=='player_stop':
                    assert rt.StopPlayer(rt.r,value);original.invoke(STOP,startup.PLAYERS[value][0])
                else:
                    assert rt.StopAll(rt.r);original.invoke(STOP_ALL)
                assert_equal(original.images(),rt.images(),original.trace,rt.trace,f'action {frame}')
                original.trace=[];rt.trace=[]
            assert rt.Frame(rt.r),rt.Error(rt.r)
            original.invoke(windows.VBLANK);original.invoke(startup.WRAPPER)
            images=original.images()
            assert_equal(images,rt.images(),original.trace,rt.trace,f'song {song_id} frame {frame}')
            block=rt.block();n=block.count
            counter=mixer.get(images,startup.init.SOUND+4);period=mixer.get(images,startup.init.SOUND+11)
            playing=(period-counter)*n;produced=(period-counter+1)*n if counter>1 else 0
            assert (block.playing_offset,block.produced_offset)==(playing,produced)
            planes=[]
            for offset in[playing,produced]:
                planes.append(tuple(bytes(mixer.get(images,startup.init.SOUND+0x350+side*0x630+offset+j)
                    for j in range(n))for side in range(2)))
            assert planes[0]==(bytes(block.right[:n]),bytes(block.left[:n])),'consumed PCM8 differs'
            assert planes[1]==(bytes(block.produced_right[:n]),bytes(block.produced_left[:n])),'produced PCM8 differs'
            raw.update(b''.join(planes[0]));raw.update(b''.join(planes[1]))
            # Independent integer timestamp lookup for each destination sample.
            values=windows.converted_pairs(images,*planes[0],64);wanted=array.array('h')
            end=(source_samples+n)*block.timer_ticks
            for sample in range(host_frames,end*windows.RATE//windows.CPU):
                index=((sample+1)*windows.CPU+block.timer_ticks*windows.RATE-1)//(block.timer_ticks*windows.RATE)-1-source_samples
                wanted.extend(values[index])
            data,consumed=rt.drain()
            assert data==wanted.tobytes(),'PCM48k timestamp oracle differs'
            assert consumed==len(data)//4
            host_frames+=consumed;source_samples+=n;pcm.extend(data)
            digest.update(f.comparable(images));digest.update(data)
            if frame%60==0:print('Passed original song frames:',frame+1,'/',frames,flush=True)
        stats=rt.stats()
        assert stats.faults==stats.underrun_samples==stats.overflow_samples==0
        assert min(array.array('h',pcm))<0<max(array.array('h',pcm)),'song produced only silence'
        with wave.open(str(out/'song_reference.wav'),'wb')as wav:
            wav.setparams((2,2,48000,0,'NONE','not compressed'));wav.writeframes(pcm)
        (out/'song_reference.pcm').write_bytes(pcm)
        return dict(api_cases=sum(counts.values()),routes=counts,song_table_entries=SONG_COUNT,
            api_instructions_covered=len(coverage&NEW_CODE),api_instruction_count=len(NEW_CODE),
            native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),song_id=song_id,song=rows[song_id],
            original_song_frames=frames,source_stereo_samples=source_samples,host_stereo_samples=host_frames,
            actions={str(k):list(x)for k,x in actions.items()},cgb_active_frames=stats.cgb_active_frames,
            pcm8_bytes_equal=True,pcm16_timestamp_oracle_equal=True,ram_io_equal=True,ordered_bus_equal=True,
            raw_pcm_results_sha256=raw.hexdigest(),pcm16_sha256=hashlib.sha256(pcm).hexdigest(),
            pcm16_fnv1a64=fnv(pcm),results_sha256=digest.hexdigest(),no_native_arm_fallback=True,
            full_game_boot=False,psg_synthesis=False,analog_output_bit_exact=False,byte_matching=False)
    finally:rt.close()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-dir',type=Path,default=ROOT/'build/native_song_validation')
    p.add_argument('--quick',action='store_true');p.add_argument('--frames',type=int,default=1800)
    p.add_argument('--song',type=int,default=1);p.add_argument('--helpers-source',type=Path)
    p.add_argument('--player-source',type=Path)
    a=p.parse_args(argv)
    if not 0<=a.song<SONG_COUNT or a.frames<24:p.error('requires valid song ID and >=24 frames')
    out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    try:
        dll=ctypes.CDLL(str(build.build(out,helpers_source=a.helpers_source,player_source=a.player_source)))
        report=run(out,dll,a.quick,80 if a.quick else a.frames,a.song)
        report.update(quick=a.quick,rom_sha1=hashlib.sha1(v.ROM).hexdigest(),
            native_build=json.loads((out/'build.json').read_text()),tool_sha256=sha(__file__),
            reference_tools_sha256={str(Path(x.__file__).relative_to(ROOT)):sha(x.__file__)
                for x in[v,f,mode,startup,mixer,windows]},host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p))
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS:',report['api_cases'],'song API cases;',report['original_song_frames'],'ROM song frames',flush=True)
        return 0
    except Exception as exc:
        (out/'failed_case.json').write_text(json.dumps(dict(error=repr(exc)),indent=2)+'\n')
        print('FAIL:',repr(exc),flush=True);return 1
if __name__=='__main__':raise SystemExit(main())
