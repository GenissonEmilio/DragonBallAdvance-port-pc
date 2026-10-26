"""Compare complete audio startup, MusicPlayer_Open and frame wrapper with ROM.

The ROM is unmodified. CpuSet copy/fill services are modeled explicitly; the
native side resolves all audio entries in C. This is not a full game boot or
an audio device/timing model.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_sound_frequency as f
import verify_sound_mode as mode
import verify_sound_initialization as init
import verify_pcm_mixer as mixer

ROOT=Path(__file__).resolve().parents[1]
STARTUP,WRAPPER,OPEN=0x0810AD34,0x0810ADAC,0x0810B474
TABLE,MEMORY=0x08A69038,0x03001EC0
PLAYERS=[struct.unpack_from('<IIBxH',v.ROM,TABLE-0x08000000+12*i)for i in range(4)]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
RANGES=[(STARTUP,0x0810AD88),(WRAPPER,0x0810ADB6),(OPEN,0x0810B4DE)]
NEW={i.address for a,b in RANGES for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}
CLEAR={i.address for i in MD.disasm(v.ROM[0x10B120:0x10B12E],0x0810B120)}
CLEAR64={i.address for i in MD.disasm(v.ROM[0x10A4AC:0x10A4C2],0x0810A4AC)}
EXPECTED=NEW|init.EXPECTED|mixer.EXPECTED|CLEAR|CLEAR64


def watched(address,width):
    return init.watched(address,width)or TABLE<=address<TABLE+48 or mixer.SOURCE<=address<mixer.SOURCE+1024


def case(route,seed,target=STARTUP,**kw):
    cfg=dict(route=route,seed=seed,target=target,mode=0,sound=init.SOUND,
        channels=init.CHANNELS,lock=f.MAGIC,dma1=0xA5120037,dma2=0x5B34007D,
        bias=255,player=v.E+0x1000,tracks=v.E+0x4000,count=16,
        chain=True,clear=0x0810A4AD)
    cfg.update(kw)
    cfg['clock']=f.CLOCKS[seed%3]+f.CLOCKS[(seed+1)%3]if target==STARTUP else[]
    if target==OPEN:cfg.update(mode=cfg['player'],a1=cfg['tracks'],a2=cfg['count'])
    return cfg


def variants(count):
    for seed,kw in enumerate([{},dict(target=OPEN,count=0),dict(target=OPEN,count=255),
        dict(target=OPEN,count=16,chain=False),dict(target=OPEN,lock=0),
        dict(target=OPEN,count=0x100),dict(target=OPEN,clear=init.DUMMY+1)]):
        yield case('guards',seed,**kw)
    for a in mode.DMA_WORDS:
        for b in mode.DMA_WORDS:yield case('startup_dma_words',a^b,dma1=a,dma2=b)
    for bias in range(256):yield case('startup_bias_bytes',bias,bias=bias)
    for lock in mode.LOCKS:yield case('startup_old_locks',lock,lock=lock)
    for a in range(len(f.LONG_CLOCKS)):
        for b in range(len(f.LONG_CLOCKS)):
            cfg=case('startup_clocks',a*7+b);cfg['clock']=f.LONG_CLOCKS[a]+f.LONG_CLOCKS[b]
            yield cfg
    for count_byte in range(256):
        for chain in [False,True]:
            yield case('open_count_bytes',count_byte*2+chain,OPEN,count=count_byte,chain=chain)
    for raw in [0x100,0x101,0x110,0x1FF,0x7FFFFFFF,0x80000000,0xFFFFFF00,0xFFFFFFFF]:
        for chain in [False,True]:
            yield case('open_wide_count',raw,OPEN,count=raw,chain=chain)
    for lock in mode.LOCKS:
        for count_byte in [0,1,16,17,255]:
            yield case('open_locks',lock,OPEN,count=count_byte,lock=lock)
    for sound in [init.SOUND,v.E+0x8000,v.I+0x2000]:
        for player in [v.E+0x1000,v.I+0x3000]:
            for tracks in [v.E+0x4000,v.I+0x4000]:
                for count_byte in [1,16,31]:
                    yield case('open_placements',sound+player+tracks+count_byte,OPEN,
                        sound=sound,player=player,tracks=tracks,count=count_byte)
    for player,tracks in [(init.SOUND,init.SOUND+0x50),(v.E+0x1000,v.E+0x1000),
        (v.E+0x1000,v.E+0x1004),(v.E+0x1000,v.E+0x1030),
        (v.E+0x1000,init.SOUND),(0x03001CF0,v.E+0x4000)]:
        for chain in [False,True]:
            yield case('open_aliases',player+tracks,OPEN,player=player,tracks=tracks,count=3,chain=chain)
    for clear in [0x0810A4AD,init.DUMMY+1]:
        for chain in [False,True]:
            yield case('open_clear_callbacks',clear,OPEN,clear=clear,chain=chain)
    for seed in range(8):yield case('startup_frames',seed)
    rng=random.Random(0xAD34ADAC)
    for seed in range(count):
        if seed%2:
            yield case('random',seed,OPEN,count=rng.getrandbits(32),chain=bool(seed&2),
                lock=rng.choice([f.MAGIC,f.MAGIC,0,f.MAGIC+1]),clear=rng.choice([0x0810A4AD,init.DUMMY+1]))
        else:yield case('random',seed,dma1=rng.getrandbits(32),dma2=rng.getrandbits(32),bias=rng.randrange(256))


def initial(cfg):
    images=[bytearray(x)for x in init.initial(cfg)]
    if cfg['target']==STARTUP:
        mixer.put(images,f.GLOBAL,v.E+0x30000,4)
    # Standalone Open receives valid RAM pointers and the installed clear slot.
    if cfg['target']==OPEN:
        mixer.put(images,0x03001CFC,cfg['clear'],4)
        mixer.put(images,cfg['sound']+32,0x0810A725 if cfg['chain']else 0,4)
        mixer.put(images,cfg['sound']+36,v.E+0x18000,4)
    return[bytes(x)for x in images]


class Oracle(init.Oracle):
    def __init__(self,cfg,images):
        super().__init__(cfg,images);self.frequency_calls=0
    def frequency(self,value):
        self.frequency_calls+=1
        original=self.cfg
        # Each nested frequency setup consumes one independently terminating
        # clock script; base oracles also assert the number of reads.
        total=len(original['clock'])
        if self.frequency_calls==1:
            end=next(i+1 for i,x in enumerate(original['clock'])if x==159 and i>0 and original['clock'][i-1]!=159)
            # Scripts starting below VBlank may reach 159 on their second read.
            total=end
        self.cfg=dict(original,target=f.SET,mode=value,clock=original['clock'][:total])
        try:f.Oracle.run(self)
        finally:self.cfg=original
    def with_mode(self,value,fn):
        original=self.cfg;self.cfg=dict(original,mode=value)
        try:fn()
        finally:self.cfg=original
    def open_player(self,player,tracks,raw):
        count=min(raw&255,16)
        if not count:return
        sound=self.read(f.GLOBAL,4);lock=self.read(sound,4)
        if lock!=f.MAGIC:return
        self.write(sound,lock+1,4)
        callback=self.read(0x03001CFC,4)
        assert callback in [0x0810A4AD,init.DUMMY+1]
        if callback==0x0810A4AD:
            for offset in range(0,64,4):self.write(player+offset,0,4)
        self.write(player+44,tracks,4);self.write(player+8,count,1)
        self.write(player+4,0x80000000,4)
        for index in range(count):self.write(tracks+80*index,0,1)
        previous=self.read(sound+32,4)
        if previous:
            self.write(player+56,previous,4)
            self.write(player+60,self.read(sound+36,4),4)
            self.write(sound+32,0,4)
        self.write(sound+36,player,4);self.write(sound+32,0x0810A725,4)
        self.write(sound,f.MAGIC,4);self.write(player+52,f.MAGIC,4)
    def run(self):
        if self.cfg['target']==OPEN:
            self.open_player(self.cfg['mode'],self.cfg['a1'],self.cfg['a2'])
        elif self.cfg['target']==STARTUP:
            self.bios_calls.append(dict(source=mixer.SOURCE,destination=mixer.RAM,control=0x04000100))
            for offset in range(0,1024,4):
                self.write(mixer.RAM+offset,self.read(mixer.SOURCE+offset,4),4)
            self.with_mode(init.SOUND,self.initialize)
            self.with_mode(init.CHANNELS,self.extend)
            original=self.cfg;self.cfg=dict(original,target=mode.MODE,mode=0x0095FC00)
            try:mode.Oracle.run(self)
            finally:self.cfg=original
            for entry in range(TABLE,TABLE+48,12):
                player=self.read(entry,4);tracks=self.read(entry+4,4);count=self.read(entry+8,1)
                self.open_player(player,tracks,count)
                self.write(player+11,self.read(entry+10,2),1)
                self.write(player+24,MEMORY,4)
        else:raise AssertionError('no independent wrapper oracle')
        assert self.clocks==len(self.cfg['clock'])
        return self.data,self.trace


def metadata(images):
    assert mixer.get(images,f.GLOBAL,4)==init.SOUND
    assert mixer.get(images,init.SOUND,4)==f.MAGIC
    assert mixer.get(images,init.SOUND+16,4)==264
    assert mixer.get(images,init.SOUND+6)==12 and mixer.get(images,init.SOUND+7)==15
    assert images[1][mixer.RAM-v.I:mixer.RAM-v.I+1024]==v.ROM[0x10A108:0x10A508]
    assert mixer.get(images,init.SOUND+32,4)==0x0810A725
    assert mixer.get(images,init.SOUND+36,4)==PLAYERS[-1][0]
    for index,(player,tracks,count,priority)in enumerate(PLAYERS):
        assert mixer.get(images,player+8)==count and mixer.get(images,player+11)==priority&255
        assert mixer.get(images,player+24,4)==MEMORY and mixer.get(images,player+44,4)==tracks
        assert mixer.get(images,player+4,4)==0x80000000 and mixer.get(images,player+52,4)==f.MAGIC
        assert mixer.get(images,player+56,4)==(0x0810A725 if index else 0)
        assert mixer.get(images,player+60,4)==(PLAYERS[index-1][0]if index else 0)
        assert all(mixer.get(images,tracks+80*n)==0 for n in range(count))
    table=list(struct.unpack_from('<36I',v.ROM,0xA67460))
    for slot,pointer in init.PATCHES:table[slot]=pointer
    assert [mixer.get(images,init.COMMANDS+i*4,4)for i in range(36)]==table
    assert all((p&~1)in v.NATIVE_AUDIO_TARGETS for p in table)


def activate(images,seed):
    """Exercise the initialized chain with controlled WAIT/FINE streams and PCM."""
    data=[bytearray(x)for x in images]
    for index,(player,tracks,count,priority)in enumerate(PLAYERS):
        mixer.put(data,player+4,0,4);mixer.put(data,player+32,150,2)
        for offset in range(80):mixer.put(data,tracks+offset,0)
        mixer.put(data,tracks,0x80);mixer.put(data,tracks+1,1)
        stream=v.E+0x20000+index*64;mixer.put(data,tracks+64,stream,4)
        for n in range(16):mixer.put(data,stream+n,0x81 if n<6 else 0xB1)
    cfg=mixer.case('active',seed,frames=264,kind=seed%2*8,loop=True,length=43)
    fixture=mixer.initial(cfg)
    channel=init.SOUND+80;wave=mixer.WAVES
    for n in range(64):mixer.put(data,channel+n,mixer.get(fixture,channel+n))
    for n in range(2064):mixer.put(data,wave+n,mixer.get(fixture,wave+n))
    # The frequency reciprocal is the real value left by startup.
    mixer.put(data,channel+32,4000+seed*317,4)
    return[bytes(x)for x in data]


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',type=int,default=256);p.add_argument('--sample-step',type=int,default=1)
    p.add_argument('--out-dir',type=Path,default=ROOT/'build/native_audio_startup_validation')
    p.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=p.parse_args(argv)
    if args.cases<0 or args.sample_step<1:p.error('invalid sampling')
    rom_sha1=hashlib.sha1(v.ROM).hexdigest()
    assert rom_sha1==json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    v.OUT=out;v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();dll=v.build_native()
    f.EXPECTED=EXPECTED
    counts={};coverage=set();digest=hashlib.sha256();executions=oracle_cases=metadata_checks=frames=0
    cpuset_controls={};io_writes=0
    for number,cfg in enumerate(variants(args.cases)):
        if cfg['route']not in ['guards','startup_frames']and number%args.sample_step:continue
        images=initial(cfg);steps=[cfg]
        if cfg['route']=='startup_frames':
            steps +=[dict(cfg,target=WRAPPER,clock=[],frame=i,mode=0,ram_code_map=[mixer.RAM,mixer.SOURCE,1024])for i in range(12)]
            steps +=[dict(cfg,reinitialize=True)]
        rom_trace=native_trace=expected_trace=None
        try:
            for step in steps:
                if step.get('frame')==2:images=activate(images,cfg['seed'])
                step=dict(step,model_cpuset_fill32=True,model_cpuset_copy32=True,cpuset_calls=[])
                f.watched=watched if step['target']!=WRAPPER else mixer.watched
                if step['target']!=WRAPPER:
                    oracle=Oracle(step,images);wanted,expected_trace=oracle.run()
                original,rom_trace,reads=f.execute(step,images,None,out,coverage)
                native,native_trace,nreads=f.execute(step,images,dll,out,coverage)
                assert f.comparable(original)==f.comparable(native),'RAM or I/O differs'
                assert rom_trace==native_trace and reads==nreads,'ordered data reads/writes differ'
                if step['target']!=WRAPPER:
                    assert f.comparable(original)==f.comparable(wanted),'independent state oracle differs'
                    assert rom_trace==expected_trace,'independent bus oracle differs'
                    assert step['cpuset_calls']==oracle.bios_calls,'modeled CpuSet parameters differ'
                    oracle_cases+=1
                if step['target']==STARTUP:metadata(original);metadata_checks+=1
                if step['target']==WRAPPER:frames+=1
                for call in step['cpuset_calls']:
                    key=hex(call['control']);cpuset_controls[key]=cpuset_controls.get(key,0)+1
                io_writes+=sum(row[0]=='write'and f.IO<=row[1]<f.IO+1024 for row in rom_trace)
                executions+=1;digest.update(f.comparable(original));digest.update(json.dumps(rom_trace).encode())
                original[1]=original[1][:0x7000]+images[1][0x7000:0x7800]+original[1][0x7800:]
                images=original
        except Exception as exc:
            (out/'failed_case.json').write_text(json.dumps(dict(case=cfg,step=step,error=repr(exc),
                rom_trace=rom_trace,native_trace=native_trace,expected_trace=expected_trace),indent=2)+'\n')
            print('FAIL:',cfg['route'],cfg['seed'],repr(exc),flush=True);return 1
        counts[cfg['route']]=counts.get(cfg['route'],0)+1
        if sum(counts.values())%128==1:print('Passed audio startup cases:',sum(counts.values()),flush=True)
    covered=coverage&NEW;missing=NEW-coverage
    if args.sample_step==1:assert not missing,[hex(a)for a in sorted(missing)]
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,sample_step=args.sample_step,
        executions=executions,independent_oracle_executions=oracle_cases,startup_metadata_checks=metadata_checks,
        initialized_players=4,initialized_tracks=sum(row[2]for row in PLAYERS),lifecycle_sequences=counts.get('startup_frames',0),
        wrapper_updates=frames,copied_ram_bytes=1024,reference_cpuset_controls=cpuset_controls,
        new_instructions_covered=len(covered),new_instruction_count=len(NEW),
        new_instruction_addresses=[hex(a)for a in sorted(covered)],missing_new_instructions=[hex(a)for a in sorted(missing)],
        player_order=[hex(row[0])for row in reversed(PLAYERS)],all_ram_equal=True,io_images_equal=True,
        ordered_reads_and_writes_equal=True,independent_startup_and_open_oracle_equal=True,
        initialized_chain_executed=True,initialized_mixer_pcm_executed=True,observed_io_writes=io_writes,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(path.relative_to(ROOT))if path.is_relative_to(ROOT)else str(path):sha(path)
            for path in [v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(path.relative_to(ROOT)):sha(path)for path in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        frequency_tool_sha256=sha(ROOT/'tools/verify_sound_frequency.py'),
        initialization_tool_sha256=sha(ROOT/'tools/verify_sound_initialization.py'),
        mixer_tool_sha256=sha(ROOT/'tools/verify_pcm_mixer.py'),compiler_sha256=sha(v.HOST_GCC),
        native_dll_sha256=sha(out/'music_player_native.dll'),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        rom_sha1=rom_sha1,results_sha256=digest.hexdigest(),reference_bios_image_used=False,
        reference_bios_copy_fill_modeled=True,rom_modified=False,byte_matching=False,full_game_boot=False,
        hardware_register_side_effects_validated=False,real_time_validated=False,audible_output_validated=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'audio startup/Open cases;',executions,'executions;',
        frames,'wrapper updates;',len(covered),'new instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
