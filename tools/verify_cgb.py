"""Native CGB state/bus comparison with ROM; flat I/O, no hardware synthesis."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_music_player as v
import verify_sound_frequency as f
import verify_sound_initialization as init

ROOT=Path(__file__).resolve().parents[1]
STOP,VOLUME,UPDATE=0x0810B834,0x0810B884,0x0810B8EC
SOUND,CHANNELS,TRACK=0x03000CC0,v.E+0x5000,v.E+0x3000
TABLE,WAVE=0x08A676C4,0x08A67000
DATA_WORDS=[0x0810B858,0x0810B860,0x0810B86C,0x0810B880,
    0x0810B90C,0x0810B958,0x0810B95C,0x0810B960,0x0810B970,0x0810B974,
    0x0810B978,0x0810B990,0x0810B994,0x0810B998,0x0810B9FC,0x0810BA00,
    0x0810BA04,0x0810BA5C,0x0810BC44,0x0810BC48,0x0810BC68,0x0810BCDC,0x0810BCE0]
PADDING=[0x0810B86A,0x0810B87E,0x0810B96E,0x0810B98E,0x0810B9FA,0x0810BA5A,
         0x0810BC42,0x0810BC66,0x0810BCDA,0x0810BD36]
EXCLUDED=set(PADDING)|{a+d for a in DATA_WORDS for d in [0,2]}
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
ALL_CODE=set()
for address in range(STOP,0x0810BD38,2):
    if address in EXCLUDED:continue
    # BL is a four-byte instruction; do not count its second half.
    word=int.from_bytes(v.ROM[address-0x08000000:address-0x08000000+2],'little')
    if word&0xF800==0xF800:continue
    instruction=next(MD.disasm(v.ROM[address-0x08000000:address-0x08000000+4],address))
    ALL_CODE.add(instruction.address)
# Both dispatches reach these branches only for a channel <=2 other than 1 or 2.
UNREACHABLE={0x0810B93E,0x0810B9F8}
EXPECTED=ALL_CODE-UNREACHABLE
BASE_WATCH=init.watched
def watched(a,n):return BASE_WATCH(a,n)or TABLE<=a<TABLE+256 or WAVE<=a<WAVE+16


def case(route,seed,target=UPDATE,number=1,**kw):
    result=dict(route=route,seed=seed,target=target,number=number,sound=SOUND,channels=CHANNELS,
        lock=f.MAGIC,clock=[],mode=0,counter=2,status=1,fields={},bias=255)
    result.update(kw)
    if target==STOP:result['mode']=kw.get('argument',number)
    elif target==VOLUME:result['mode']=result['channels']+64*(number-1)
    return result


def variants(count):
    for seed in range(8):
        yield case('guards',seed,number=seed%4+1,status=[0,0x80,0xC0,4,3,2,1,0x40][seed],
                   counter=seed,fields={4:0 if seed&1 else 3,5:0 if seed&2 else 3,6:0 if seed&4 else 128})
    for number in [1,2,3]:yield case('guards',number+8,STOP,argument=0xABCD0100|number)
    for number in range(1,5):
        yield case('guards',number+11,number=number,bias=0,frequency=2,fields={1:8,0x1D:2})
    for length in [0,129]:yield case('guards',length+16,status=4,fields={13:length})
    for number in range(1,5):
        yield case('guards',number+150,number=number,status=2,fields={6:0,9:1,11:0})
    for argument in range(512):yield case('stop_arguments',argument,STOP,argument=argument|(0xABCD0000 if argument&1 else 0))
    for right in range(256):
        for left in [0,1,7,8,15,63,127,128,254,255]:
            yield case('volume_stereo',right*256+left,VOLUME,fields={2:right,3:left,6:255})
    for sustain in range(256):yield case('volume_sustain',sustain,VOLUME,fields={2:255,3:255,6:sustain})
    for number in range(1,5):
        for status in range(256):yield case('status_bytes',status+256*number,number=number,status=status)
    for counter in range(256):yield case('counter_bytes',counter,counter=counter,status=3)
    for offset in [4,5,7]:
        for value in range(256):
            yield case('rate_bytes',offset*256+value,number=value%4+1,status=0x80 if offset==4 else 3 if offset==5 else 0x43,
                       fields={4:0,5:0,7:0,offset:value})
    for number in range(1,5):
        for phase in [0,1,2,3]:
            for value in [0,1,2,7,8,15,16,31,63,127,128,129,254,255]:
                yield case('envelope_edges',number*1024+phase*256+value,number=number,status=phase|0x40 if phase==0 else phase,
                    fields={9:value,11:0,12:value,13:value},counter=1)
    for number in range(1,5):
        for bias in range(256):
            yield case('bias_bytes',number*256+bias,number=number,bias=bias,fields={1:8,0x1D:2},
                       frequency=[0,0x7FD,0xFFFFFFFF,0xF1234567][bias%4])
    for wave in [WAVE,v.E+0x20000,v.I+0x6000,f.IO+0x8C,f.IO+0x90,f.IO+0x94]:
        for same in [False,True]:
            for length in [0,255]:yield case('wave_copy',wave+int(same)+length,number=3,status=0x80,wave=wave,same=same,fields={0x1E:length})
    for value in range(256):yield case('wave_volume_reads',value,number=3,fields={9:value,0x1A:0x80,0x1D:1})
    for value in range(256):yield case('hardware_flags',value,number=value%4+1,fields={0x1D:value,0x1F:value},counter=2)
    for seed in range(8):yield case('lifecycle',seed,counter=0,sound=SOUND if seed&1 else v.E+0x2000)
    for number in range(1,5):
        for seed in range(4):yield case('track_stop',seed,number=number,target=0x0810A98C,mode=0,a1=TRACK)
    rng=random.Random(0xB834B8EC)
    for seed in range(count):
        fields={offset:rng.randrange(256)for offset in [1,2,3,4,5,6,7,9,11,12,13,0x19,0x1A,0x1B,0x1C,0x1D,0x1E,0x1F]}
        yield case('random',seed,number=seed%4+1,status=rng.randrange(256),counter=rng.randrange(256),
                   fields=fields,bias=rng.randrange(256),frequency=rng.getrandbits(32),
                   channels=[CHANNELS,v.I+0x3000,v.E+0x10000][seed%3])


def put(images,a,value,n=1):
    for base,data in [(v.E,images[0]),(v.I,images[1]),(f.IO,images[2])]:
        if base<=a and a+n<=base+len(data):
            data[a-base:a-base+n]=(value&((1<<(8*n))-1)).to_bytes(n,'little');return
    raise AssertionError(hex(a))


def records(images,cfg):
    for number in range(1,5):
        p=cfg['channels']+64*(number-1)
        for offset in range(64):put(images,p+offset,0)
        fields={0:cfg['status']if number==cfg['number']else 0,1:number,2:120,3:80,4:2,5:3,6:128,7:4,
            9:7,10:12,11:1,12:128,13:3,0x19:6,0x1A:0x40,0x1B:0xFF,0x1C:0x11<<(number-1),0x1D:3,0x1E:16,0x1F:8}
        if number==cfg['number']:fields.update(cfg['fields'])
        for offset,value in fields.items():put(images,p+offset,value)
        put(images,p+0x20,cfg.get('frequency',0x765),4)
        put(images,p+0x24,cfg.get('wave',WAVE),4)
        put(images,p+0x28,cfg.get('wave',WAVE)if cfg.get('same')else 0,4)


def initial(cfg):
    images=[bytearray(x)for x in f.initial(cfg)]
    put(images,cfg['sound']+0x1C,cfg['channels'],4);put(images,cfg['sound']+10,cfg['counter'])
    put(images,cfg['sound']+0x2C,STOP+1,4);put(images,f.IO+0x89,cfg['bias'])
    records(images,cfg)
    if cfg['route']=='track_stop':
        p=cfg['channels']+64*(cfg['number']-1)
        put(images,TRACK,0x80);put(images,TRACK+0x20,p,4)
        put(images,p,0x80);put(images,p+0x34,0,4);put(images,p+0x2C,TRACK,4)
    return [bytes(x)for x in images]


class Oracle(init.Oracle):
    def stop(self,number):
        for offset,value in {1:[(0x63,8),(0x65,128)],2:[(0x69,8),(0x6D,128)],3:[(0x70,0)]}.get(number&255,[(0x79,8),(0x7D,128)]):
            self.write(f.IO+offset,value,1)
    def volume(self,p):
        r=self.read(p+2,1);l=self.read(p+3,1)
        direction=15 if r>=l and r//2>=l else 240 if r<l and l//2>=r else 255
        self.write(p+27,direction,1)
        total=self.read(p+3,1);total+=self.read(p+2,1);total>>=4
        self.write(p+10,total,1)
        if direction!=255 and total>15:self.write(p+10,15,1)
        sustain=self.read(p+6,1);goal=self.read(p+10,1)
        self.write(p+25,(sustain*goal+15)>>4,1)
        mask=self.read(p+28,1);pan=self.read(p+27,1);self.write(p+27,mask&pan,1)
    def update(self):
        sound=self.read(f.GLOBAL,4);tick=self.read(sound+10,1);self.write(sound+10,tick-1 if tick else 14,1)
        base=self.read(sound+28,4)
        for number,regs in enumerate([(0x60,0x62,0x63,0x64,0x65),(0x61,0x68,0x69,0x6C,0x6D),
            (0x70,0x72,0x73,0x74,0x75),(0x71,0x78,0x79,0x7C,0x7D)],1):
            p=base+64*(number-1)
            b=lambda offset:self.read(p+offset,1)
            w=lambda offset,value:self.write(p+offset,value,1)
            r0,r1,r2,r3,r4=[f.IO+x for x in regs]
            status=b(0)
            if not status&0xC7:continue
            counter=self.read(sound+10,1);env=self.read(r2,1)
            state='envelope'
            if status&128:
                state='stop'
                if not status&64:
                    w(0,3);w(29,3);self.volume(p)
                    if number<=2:
                        if number==1:self.write(r0,b(31),1)
                        value=self.read(p+36,4)<<6;value+=b(30);self.write(r1,value,1)
                    elif number==3:
                        source=self.read(p+36,4);cached=self.read(p+40,4)
                        if source!=cached:
                            self.write(r0,64,1);source=self.read(p+36,4)
                            for off in [0,4,8,12]:
                                value=self.read(source+off,4);self.write(f.IO+0x90+off,value,4)
                            self.write(p+40,source,4)
                        self.write(r0,0,1);self.write(r1,b(30),1);w(26,192 if b(30)else 128)
                    else:
                        self.write(r1,b(30),1);self.write(r3,self.read(p+36,4)<<3,1)
                    if number!=3:env=b(4)+8;w(26,64 if b(30)else 0)
                    attack=b(4);w(11,attack);state='attack_end'if attack==0 else'decrement'
                    if attack:w(9,0)
            elif status&4:
                length=(b(13)-1)&255;w(13,length);state='hardware'if f.signed(length<<24)>0 else'stop'
            elif status&64 and status&3:
                w(0,status&252);rate=b(7);w(11,rate)
                state='echo'if rate==0 else'decrement'
                if rate:
                    w(29,b(29)|1)
                    if number!=3:env=b(7)
            while state not in ['hardware','stopped']:
                if state=='stop':
                    self.stop(number);w(0,0);state='stopped'
                elif state=='envelope':
                    if b(11):state='decrement';continue
                    if number==3:w(29,b(29)|1)
                    self.volume(p);phase=b(0)&3
                    if phase==0:
                        value=(b(9)-1)&255;w(9,value)
                        state='echo'if f.signed(value<<24)<=0 else'release_reload'
                    elif phase==1:state='sustain'
                    elif phase==2:
                        value=(b(9)-1)&255;w(9,value);goal=b(25)
                        state='decay_reload'if f.signed(value<<24)>f.signed(goal<<24)else'decay_end'
                    else:
                        value=(b(9)+1)&255;w(9,value)
                        state='attack_reload'if value<b(10)else'attack_end'
                elif state.endswith('_reload'):
                    w(11,b({'release_reload':7,'decay_reload':5,'attack_reload':4}[state]));state='decrement'
                elif state=='attack_end':
                    w(0,b(0)-1);rate=b(5);w(11,rate)
                    if not rate:state='decay_end';continue
                    w(29,b(29)|1);w(9,b(10))
                    if number!=3:env=b(5)
                    state='decrement'
                elif state=='decay_end':
                    if not b(6):w(0,b(0)&252);state='echo';continue
                    w(0,b(0)-1);w(29,b(29)|1)
                    if number!=3:env=8
                    state='sustain'
                elif state=='sustain':
                    w(9,b(25));w(11,7);state='decrement'
                elif state=='decrement':
                    w(11,b(11)-1);state='envelope'if counter==0 else'hardware';counter-=int(counter==0)
                elif state=='echo':
                    value=b(12);value=(value*b(10)+255)>>8;w(9,value)
                    if not value:state='stop';continue
                    w(0,b(0)|4);w(29,b(29)|1)
                    if number!=3:env=8
                    state='hardware'
                else:raise AssertionError(state)
            if state=='hardware':
                if b(29)&2:
                    if number<4 and b(1)&8:
                        bias=self.read(f.IO+0x89,1)
                        if bias<128:
                            frequency=self.read(p+32,4);self.write(p+32,(frequency+(2 if bias<64 else 1))&(0x7FC if bias<64 else 0x7FE),4)
                    value=self.read(r3,1)&8 if number==4 else 0
                    value|=self.read(p+32,4);self.write(r3,value,1)
                    high=b(26)&192;high+=b(33);w(26,high);self.write(r4,high&255,1)
                if b(29)&1:
                    value=self.read(f.IO+0x81,1);value&=~b(28);value|=b(27);self.write(f.IO+0x81,value,1)
                    if number==3:
                        volume=b(9);self.write(r2,self.read(TABLE+volume,1),1)
                        if b(26)&128:
                            self.write(r0,128,1);self.write(r4,b(26),1);w(26,b(26)&127)
                    else:
                        self.write(r2,(b(9)<<4)+(env&15),1);self.write(r4,b(26)|128,1)
                        if number==1 and not self.read(r0,1)&8:self.write(r4,b(26)|128,1)
            w(29,0)
    def run(self):
        target=self.cfg['target']
        if target==STOP:self.stop(self.cfg['mode'])
        elif target==VOLUME:self.volume(self.cfg['mode'])
        elif target==UPDATE:self.update()
        elif target==0x0810A98C:
            track=self.cfg['a1']
            if self.read(track,1)&128:
                p=self.read(track+32,4)
                while p:
                    if self.read(p,1):
                        kind=self.read(p+1,1)&7
                        if kind:
                            sound=self.read(f.GLOBAL,4);assert self.read(sound+44,4)==STOP+1;self.stop(kind)
                        self.write(p,0,1)
                    self.write(p+44,0,4);p=self.read(p+52,4)
                self.write(track+32,0,4)
        else:return super().run()
        return self.data,self.trace


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512);parser.add_argument('--sample-step',type=int,default=1)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_cgb_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0 or args.sample_step<1:parser.error('invalid case count or sample step')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1'];assert hashlib.sha1(v.ROM).hexdigest()==expected
    out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    v.OUT=out;v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();dll=v.build_native()
    f.EXPECTED=EXPECTED|init.EXPECTED|{i.address for i in MD.disasm(v.ROM[0x10A98C:0x10A9CC],0x0810A98C)}
    f.watched=watched
    counts={};coverage=set();executions=io_writes=wave_writes=callbacks=frames=0;digest=hashlib.sha256()
    for index,cfg in enumerate(variants(args.cases)):
        if cfg['route']not in ['guards','lifecycle','track_stop']and index%args.sample_step:continue
        images=initial(cfg);steps=[cfg]
        if cfg['route']=='lifecycle':
            steps=[dict(cfg,target=init.INIT,mode=cfg['sound'],clock=f.CLOCKS[cfg['seed']%3]),
                   dict(cfg,target=init.EXTEND,mode=cfg['channels'],clock=[])]
            steps +=[dict(cfg,target=UPDATE,mode=0,frame=frame,clock=[],installed=True)for frame in range(24)]
            steps +=[dict(cfg,target=STOP,mode=cfg['number'],clock=[],installed=True)]
        rom_trace=native_trace=wanted_trace=None
        try:
            for step in steps:
                if step.get('frame')in [0,16]:
                    images=[bytearray(x)for x in images]
                    # All four channels start together from the extended records.
                    for number in range(1,5):
                        config=dict(cfg,number=number,status=0x80,fields={4:2,5:2,6:128,7:2})
                        p=cfg['channels']+64*(number-1)
                        sample=initial(config)
                        data,off=(sample[0],p-v.E)if p<v.I else(sample[1],p-v.I)
                        for n in range(64):put(images,p+n,data[off+n])
                    images=[bytes(x)for x in images]
                if step.get('frame')in [8,20]:
                    images=[bytearray(x)for x in images]
                    for number in range(4):
                        p=cfg['channels']+number*64
                        data=images[0]if p<v.I else images[1];off=p-(v.E if p<v.I else v.I)
                        put(images,p,data[off]|64)
                    images=[bytes(x)for x in images]
                if step.get('installed'):
                    pointer=init.image_word(images,cfg['sound']+(0x28 if step['target']==UPDATE else 0x2C))
                    assert pointer==step['target']+1;step=dict(step,target=pointer&~1);callbacks+=1
                    frames+=step['target']==UPDATE
                step=dict(step,model_cpuset_fill32=True,cpuset_calls=[])
                oracle=Oracle(step,images);wanted,wanted_trace=oracle.run()
                original,rom_trace,reads=f.execute(step,images,None,out,coverage)
                candidate,native_trace,nreads=f.execute(step,images,dll,out,coverage)
                assert f.comparable(original)==f.comparable(candidate)==f.comparable(wanted),'state differs'
                assert rom_trace==native_trace==wanted_trace,'ordered bus trace differs'
                assert reads==nreads==oracle.global_reads
                assert step['cpuset_calls']==oracle.bios_calls
                executions+=1;io_writes+=sum(row[0]=='write'and f.IO<=row[1]<f.IO+1024 for row in rom_trace)
                wave_writes+=sum(row[0]=='write'and f.IO+0x90<=row[1]<f.IO+0xA0 for row in rom_trace)
                digest.update(f.comparable(original));digest.update(json.dumps(rom_trace).encode())
                original[1]=original[1][:0x7000]+images[1][0x7000:0x7800]+original[1][0x7800:];images=original
        except Exception as exc:
            (out/'failed_case.json').write_text(json.dumps(dict(case=cfg,error=repr(exc),rom_trace=rom_trace,native_trace=native_trace,oracle_trace=wanted_trace),indent=2)+'\n')
            print('FAIL:',cfg['route'],cfg['seed'],repr(exc),flush=True);return 1
        counts[cfg['route']]=counts.get(cfg['route'],0)+1
        if sum(counts.values())%256==1:print('Passed CGB cases:',sum(counts.values()),flush=True)
    missing=EXPECTED-coverage
    if args.sample_step==1:assert not missing,[hex(a)for a in sorted(missing)]
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),executions=executions,routes=counts,random_cases=args.cases,sample_step=args.sample_step,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],all_ram_equal=True,io_images_equal=True,
        ordered_reads_and_writes_equal=True,independent_model_equal=True,native_cgb_fallback_to_arm=False,
        cgb_instructions_covered=len(coverage&EXPECTED),cgb_instruction_addresses=[hex(a)for a in sorted(coverage&EXPECTED)],
        cgb_reachable_instruction_count=len(EXPECTED),cgb_missing_instruction_addresses=[hex(a)for a in sorted(missing)],
        cgb_unreachable_instruction_addresses=[hex(a)for a in UNREACHABLE],observed_io_writes=io_writes,observed_wave_ram_writes=wave_writes,
        lifecycle_sequences=counts.get('lifecycle',0),installed_callback_calls=callbacks,installed_update_frames=frames,
        cgb_callbacks_executed=True,cgb_callbacks_pending_native=[],stop_update_volume_in_c=True,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        frequency_tool_sha256=sha(ROOT/'tools/verify_sound_frequency.py'),initialization_tool_sha256=sha(ROOT/'tools/verify_sound_initialization.py'),
        native_dll_sha256=sha(out/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),rom_sha1=expected,
        host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),results_sha256=digest.hexdigest(),byte_matching=False,full_game_boot=False,
        hardware_register_side_effects_validated=False,real_time_validated=False,audible_output_validated=False,
        reference_bios_image_used=False,cpu='Unicorn ARM926; flat I/O, modeled setup CpuSet; no hardware timing')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'CGB cases;',executions,'executions;',report['cgb_instructions_covered'],'instructions',flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
