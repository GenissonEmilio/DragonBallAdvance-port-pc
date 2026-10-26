"""Differential native audio host: ROM VSync/mixer, DMA blocks, PCM16 and clocks.

WASAPI playback is a separate, explicitly invoked device test. No game boot,
PSG synthesis or analog speaker/DAC equivalence is claimed.
"""
from pathlib import Path
import argparse,array,bisect,ctypes,hashlib,json,random,struct,types
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import build_windows_audio as build
import verify_music_player as v
import verify_sound_frequency as f
import verify_sound_mode as mode
import verify_sound_initialization as init
import verify_audio_startup as startup
import verify_pcm_mixer as mixer

ROOT=Path(__file__).resolve().parents[1]
CPU,FRAME,RATE=16777216,280896,48000
VBLANK=0x0810A6D8
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
VBLANK_CODE={i.address for i in MD.disasm(v.ROM[0x10A6D8:0x10A71A],VBLANK)}
OBS=ctypes.CFUNCTYPE(None,ctypes.c_void_p,*[ctypes.c_uint32]*4)
class Stats(ctypes.Structure):
    _fields_=[(k,ctypes.c_uint64)for k in ['frames','source_samples','converted_samples','consumed_samples',
        'underrun_samples','overflow_samples','max_queued','cycles','faults','cgb_active_frames']]
class Block(ctypes.Structure):
    _fields_=[(k,ctypes.c_uint32)for k in ['count','playing_offset','produced_offset','timer_ticks']]+[
        (k,ctypes.c_uint8*704)for k in ['right','left','produced_right','produced_left']]


class Runtime:
    def __init__(self,dll):
        self.dll=dll;self.trace=[];self.filter=startup.watched
        def observe(user,write,address,width,value):
            if self.filter(address,width):self.trace.append(('write'if write else'read',address,width,value))
        self.observer=OBS(observe)
        signatures={
            'Create':([ctypes.c_void_p,ctypes.c_size_t],ctypes.c_void_p),
            'Destroy':([ctypes.c_void_p],None),'Initialize':([ctypes.c_void_p],ctypes.c_int),
            'Frame':([ctypes.c_void_p],ctypes.c_int),'Mode':([ctypes.c_void_p,ctypes.c_uint],ctypes.c_int),
            'Suspend':([ctypes.c_void_p,ctypes.c_int],ctypes.c_int),
            'Demo':([ctypes.c_void_p],ctypes.c_int),'Gain':([ctypes.c_void_p,ctypes.c_uint],None),
            'Read':([ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t],ctypes.c_size_t),
            'Queued':([ctypes.c_void_p],ctypes.c_size_t),
            'Stats':([ctypes.c_void_p,ctypes.POINTER(Stats)],None),
            'Block':([ctypes.c_void_p,ctypes.POINTER(Block)],None),
            'Observe':([ctypes.c_void_p,OBS,ctypes.c_void_p],None),
            'Memory':([ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int],ctypes.c_int),
            'ClockTrace':([ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t],ctypes.c_size_t),
            'Error':([ctypes.c_void_p],ctypes.c_char_p)}
        for name,(args,result)in signatures.items():
            fn=getattr(dll,'Dbaa_AudioRuntime'+name);fn.argtypes=args;fn.restype=result
            setattr(self,name,fn)
        data=ctypes.create_string_buffer(v.ROM)
        self.r=self.Create(data,len(v.ROM));assert self.r,'runtime rejected configured ROM'
        self.Observe(self.r,self.observer,None)
    def close(self):self.Destroy(self.r)
    def memory(self,address,data=None,size=None):
        buffer=ctypes.create_string_buffer(data)if data is not None else ctypes.create_string_buffer(size)
        assert self.Memory(self.r,address,buffer,len(data)if data is not None else size,int(data is not None))
        return buffer.raw[:len(data)if data is not None else size]
    def images(self):return[self.memory(a,size=n)for a,n in [(v.E,0x40000),(v.I,0x8000),(f.IO,1024)]]
    def clocks(self):
        data=(ctypes.c_uint8*1024)();n=self.ClockTrace(self.r,data,1024);return list(data[:n])
    def stats(self):
        s=Stats();self.Stats(self.r,ctypes.byref(s));return s
    def block(self):
        b=Block();self.Block(self.r,ctypes.byref(b));return b
    def drain(self,extra=0):
        n=self.Queued(self.r)+extra;data=(ctypes.c_int16*(2*n))()
        actual=self.Read(self.r,data,n)
        return bytes(data),actual
    def reset(self):
        for a,n in [(v.E,0x40000),(v.I,0x8000),(f.IO,1024)]:self.memory(a,bytes(n))
        self.filter=startup.watched;self.trace=[]
        assert self.Initialize(self.r),self.Error(self.r)


def reference(cfg,images,out,coverage,watch):
    f.watched=watch;f.EXPECTED=startup.EXPECTED|VBLANK_CODE
    result,trace,reads=f.execute(dict(cfg,model_cpuset_fill32=True,model_cpuset_copy32=True,
        cpuset_calls=[]),images,None,out,coverage)
    # The original's dead stack is not persistent game state.
    result[1]=result[1][:0x7000]+images[1][0x7000:0x7800]+result[1][0x7800:]
    return result,trace


def fixture(images,index,kind,loop,reverb,control=0xA90E):
    images=[bytearray(x)for x in images]
    cfg=mixer.case('host_pcm',index,frames=struct.unpack_from('<H',v.ROM,0xA675D4+2*(index-1))[0],
        kind=kind,loop=loop,length=43,loop_start=7,step=17891,voices=1)
    data=mixer.initial(cfg);channel=init.SOUND+80;wave=mixer.WAVES
    for n in range(64):mixer.put(images,channel+n,mixer.get(data,channel+n))
    for n in range(2064):mixer.put(images,wave+n,mixer.get(data,wave+n))
    mixer.put(images,init.SOUND+5,reverb);mixer.put(images,f.IO+0x82,control,2)
    return[bytes(x)for x in images]


def converted_pairs(images,right,left,gain):
    control=mixer.get(images,f.IO+0x82,2);sound=init.SOUND
    active=(mixer.get(images,sound,4)-f.MAGIC)&0xFFFFFFFF<=1
    enabled=bool(mixer.get(images,f.IO+0x84,2)&128)and bool(mixer.get(images,f.IO+0x102,2)&128)
    dma=[bool(mixer.get(images,f.IO+a,2)&0x8000)for a in [0xC6,0xD2]]
    result=[]
    def quantize(value):
        value=value*gain
        value=value//2 if value>=0 else-((-value)//2)
        return max(-32768,min(32767,value))
    for a,b in zip(right,left):
        a=mixer.s8(a)if active and enabled and dma[0]else 0
        b=mixer.s8(b)if active and enabled and dma[1]else 0
        va=a*(2 if control&4 else 1);vb=b*(2 if control&8 else 1)
        l=(va if control&0x200 else 0)+(vb if control&0x2000 else 0)
        r=(va if control&0x100 else 0)+(vb if control&0x1000 else 0)
        result.append((quantize(l),quantize(r)))
    return result


def run(out,dll,quick=False):
    rt=Runtime(dll);coverage=set();digest=hashlib.sha256()
    sequences=frames=rom_executions=source_samples=host_samples=0
    try:
        configs=[(i,k,l,rv,0xA90E,g,False)for i in([5]if quick else range(1,13))
            for k in([8]if quick else [0,8])for l in([True]if quick else [False,True])
            for rv in([0]if quick else [0,31,127])for g in [256]]
        if not quick:
            configs +=[(5,8,True,0,c,g,False)for c in [0xA90E,0x9A0E,0xBB0E,0x880E,0xA902]
                for g in [0,64,256]]
            configs +=[(5,8,True,0,0xA90E,256,True)]
        for index,kind,loop,reverb,control,gain,pause in configs:
            initial=[bytes(0x40000),bytes(0x8000),bytes(1024)]
            rt.reset();native=rt.images()
            cfg=dict(seed=0,mode=0,target=startup.STARTUP,clock=rt.clocks())
            images,trace=reference(cfg,initial,out,coverage,startup.watched);rom_executions+=1
            assert f.comparable(native)==f.comparable(images),'native startup state differs'
            assert trace==rt.trace,'native startup bus differs'
            startup.metadata(images)
            clock_before=len(rt.clocks());rt.trace=[]
            assert rt.Mode(rt.r,index)
            cfg=dict(seed=0,mode=index<<16,target=mode.MODE,clock=rt.clocks()[clock_before:])
            images,trace=reference(cfg,images,out,coverage,startup.watched);rom_executions+=1
            assert trace==rt.trace and f.comparable(rt.images())==f.comparable(images),'host frequency setup differs'
            images=fixture(images,index,kind,loop,reverb,control)
            for address,data in zip([v.E,v.I,f.IO],images):rt.memory(address,data)
            rt.Gain(rt.r,gain)
            ends=[];values=[];actual=bytearray();cycles=0
            previous=None;before=rt.stats()
            for frame in range(4 if quick else 20):
                if pause and frame in [6,8]:
                    rt.filter=mixer.watched;rt.trace=[]
                    assert rt.Suspend(rt.r,int(frame==6))
                    cfg=dict(seed=0,mode=0,clock=[],target=mode.OFF if frame==6 else f.VSYNC)
                    images,trace=reference(cfg,images,out,coverage,mixer.watched);rom_executions+=1
                    assert rt.trace==trace and f.comparable(rt.images())==f.comparable(images),'suspend/resume differs'
                    previous=None
                rt.filter=mixer.watched;rt.trace=[]
                assert rt.Frame(rt.r),rt.Error(rt.r)
                config=dict(seed=frame,mode=0,clock=[],target=VBLANK)
                images,vt=reference(config,images,out,coverage,mixer.watched)
                config.update(target=startup.WRAPPER,ram_code_map=[mixer.RAM,mixer.SOURCE,1024])
                images,mt=reference(config,images,out,coverage,mixer.watched);rom_executions+=2
                assert rt.trace==vt+mt,'native VBlank/wrapper ordered bus differs'
                assert f.comparable(rt.images())==f.comparable(images),'native frame RAM/I/O differs'
                block=rt.block();n=block.count;counter=mixer.get(images,init.SOUND+4)
                period=mixer.get(images,init.SOUND+11)
                active=((mixer.get(images,init.SOUND,4)-f.MAGIC)&0xFFFFFFFF)<=1
                playing=(period-counter)*n if active else 0
                produced=(period-counter+1)*n if active and counter>1 else 0
                assert(block.playing_offset,block.produced_offset)==(playing,produced),'DMA block selection differs'
                planes=[]
                for offset in [playing,produced]:
                    planes.append(tuple(bytes(mixer.get(images,init.SOUND+0x350+side*0x630+offset+j)
                        for j in range(n))for side in range(2)))
                assert planes[0]==(bytes(block.right[:n]),bytes(block.left[:n])),'consumed PCM differs'
                assert planes[1]==(bytes(block.produced_right[:n]),bytes(block.produced_left[:n])),'produced PCM differs'
                if previous is not None:assert planes[0]==previous,'one-block FIFO pipeline differs'
                previous=planes[1]
                for pair in converted_pairs(images,*planes[0],gain):
                    cycles+=block.timer_ticks
                    ends.append(cycles*RATE);values.append(pair)
                chunk,consumed=rt.drain();actual.extend(chunk)
                assert consumed==len(chunk)//4
                assert len(actual)//4==cycles*RATE//CPU,'PCM48k sample count/drift differs'
                frames+=1;source_samples+=n
                digest.update(f.comparable(images));digest.update(chunk)
            # Independent timestamp lookup, not the C phase accumulator loop.
            wanted=array.array('h')
            for sample in range(cycles*RATE//CPU):
                wanted.extend(values[bisect.bisect_left(ends,(sample+1)*CPU)])
            assert actual==wanted.tobytes(),'PCM16 channel/gain/hold conversion differs'
            after=rt.stats()
            assert after.converted_samples-before.converted_samples==len(wanted)//2
            assert after.underrun_samples==after.overflow_samples==after.faults==0
            host_samples+=len(wanted)//2;sequences+=1
            if sequences%16==1:print('Passed Windows PCM sequences:',sequences,flush=True)
        # Entire VSync byte domain, guard locks, period values and DMA repeats.
        dll.Dbaa_AudioVBlank.argtypes=[ctypes.POINTER(v.Host)]
        def dispatch(host,target,a,b,c):dll.Dbaa_AudioVBlank(host);return 0
        adapter=types.SimpleNamespace(Dbaa_AudioCall=dispatch)
        blank_cases=0
        cases=[(lock,count,6,0xFFFFFFFF,0x02000000)for lock in
            [f.MAGIC,f.MAGIC+1,0,f.MAGIC+10]for count in range(0,256,17 if quick else 1)]
        if not quick:
            cases +=[(f.MAGIC,0,p,0,0)for p in range(256)]
            cases +=[(f.MAGIC,1,6,a,b)for a in mode.DMA_WORDS for b in mode.DMA_WORDS]
        for lock,count,period,a,b in cases:
            cfg=dict(seed=count,mode=0,target=VBLANK,clock=[],sound=init.SOUND,lock=lock)
            images=[bytearray(x)for x in f.initial(cfg)]
            for address,value,width in [(init.SOUND+4,count,1),(init.SOUND+11,period,1),
                (f.IO+0xC4,a,4),(f.IO+0xD0,b,4)]:mixer.put(images,address,value,width)
            f.watched=mixer.watched;f.EXPECTED=VBLANK_CODE
            original,ot,reads=f.execute(cfg,images,None,out,coverage)
            native,nt,nreads=f.execute(cfg,images,adapter,out,coverage)
            assert f.comparable(original)==f.comparable(native)and ot==nt and reads==nreads,'VSync reference differs'
            blank_cases+=1;rom_executions+=1
        assert VBLANK_CODE<=coverage
        dll.Dbaa_AudioDeadline.argtypes=[ctypes.c_uint64,ctypes.c_uint64];dll.Dbaa_AudioDeadline.restype=ctypes.c_uint64
        rng=random.Random(0x48000);deadline_cases=0
        for frequency in [3579545,10000000,3000000000]:
            for frame in [0,1,59,60,3600,24*3600*60,*[rng.randrange(6000000)for _ in range(100 if quick else 10000)]]:
                assert dll.Dbaa_AudioDeadline(frame,frequency)==frame*FRAME*frequency//CPU,'rational QPC drift'
                deadline_cases+=1
        for frame,freq in [(1,0),(2**64-1,10000000),(1,2**64-1)]:
            assert dll.Dbaa_AudioDeadline(frame,freq)==2**64-1
        # Ring behavior and a long virtual run use the same exported runtime.
        # No observer callbacks or host wall-clock waits participate here.
        rt.Observe(rt.r,OBS(),None);rt.reset();rt.Observe(rt.r,OBS(),None)
        silent,actual=rt.drain(16)
        assert actual==0 and silent==bytes(64)
        assert rt.stats().underrun_samples==16
        count=0
        while rt.Frame(rt.r):count+=1
        assert count==20 and rt.stats().overflow_samples>0 and rt.stats().faults==1
        rt.close();rt=Runtime(dll);rt.reset();rt.Observe(rt.r,OBS(),None)
        assert rt.Demo(rt.r);rt.Gain(rt.r,256)
        long_frames=200 if quick else 36000;before=rt.stats()
        packets=nonzero=0
        for frame in range(long_frames):
            assert rt.Frame(rt.r),rt.Error(rt.r)
            while rt.Queued(rt.r):
                n=min(rt.Queued(rt.r),[103,479,1024][packets%3])
                data=(ctypes.c_int16*(2*n))()
                assert rt.Read(rt.r,data,n)==n
                nonzero+=any(data);packets+=1
        after=rt.stats()
        assert after.converted_samples-before.converted_samples==long_frames*FRAME*RATE//CPU
        assert after.consumed_samples==after.converted_samples and after.underrun_samples==after.overflow_samples==after.faults==0
        assert nonzero>0 and rt.Queued(rt.r)==0
        return dict(sequences=sequences,game_frames=frames,rom_executions=rom_executions,
            source_samples=source_samples,host_stereo_samples=host_samples,vsync_cases=blank_cases,
            vsync_instructions_covered=len(coverage&VBLANK_CODE),vsync_instruction_count=len(VBLANK_CODE),
            rational_deadline_cases=deadline_cases,pcm_bytes_equal=True,ram_io_equal=True,ordered_bus_equal=True,
            virtual_long_run_frames=long_frames,virtual_long_run_samples=after.converted_samples-before.converted_samples,
            virtual_long_run_packets=packets,ring_overflow_rejected=True,ring_underflow_zero_filled=True,
            suspend_resume_reference_equal=not quick,
            fifo_one_block_pipeline_equal=True,pcm16_timestamp_oracle_equal=True,nominal_modes=list(range(1,13))if not quick else[5],
            source_timer_ticks=[FRAME//n for n in struct.unpack_from('<12H',v.ROM,0xA675D4)],
            results_sha256=digest.hexdigest(),no_native_arm_fallback=True,
            byte_matching=False,full_game_boot=False,psg_synthesis=False,analog_output_bit_exact=False,
            physical_audibility_confirmed=False,windows_device_test_included=False)
    finally:rt.close()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-dir',type=Path,default=ROOT/'build/native_windows_audio_validation')
    p.add_argument('--runtime-source',type=Path);p.add_argument('--quick',action='store_true')
    a=p.parse_args(argv);out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    try:
        assert hashlib.sha1(v.ROM).hexdigest()==json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
        dll=ctypes.CDLL(str(build.build(out,a.runtime_source)))
        report=run(out,dll,a.quick)
    except Exception as exc:
        (out/'failed_case.json').write_text(json.dumps(dict(error=repr(exc)),indent=2)+'\n')
        print('FAIL:',repr(exc),flush=True);return 1
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    report.update(rom_sha1=hashlib.sha1(v.ROM).hexdigest(),quick=a.quick,tool_sha256=sha(__file__),
        reference_tools_sha256={str(path.relative_to(ROOT)):sha(path)for path in [
            ROOT/'tools/verify_music_player.py',ROOT/'tools/verify_sound_frequency.py',
            ROOT/'tools/verify_audio_startup.py',ROOT/'tools/verify_pcm_mixer.py']},
        native_build=json.loads((out/'build.json').read_text()),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['sequences'],'sequences;',report['game_frames'],'frames;',
        report['vsync_cases'],'VSync cases;',report['host_stereo_samples'],'PCM48k samples',flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
