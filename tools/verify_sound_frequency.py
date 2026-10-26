"""Compare frequency setup and VSync-on native C with the unmodified USA ROM.

The clock supplies a finite VCOUNT read script. RAM, flat I/O images and ordered
bus operations must also agree with an independent Python state transition.
Device side effects, real time and audible output are outside this model.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,os,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from unicorn import UC_HOOK_INTR
import verify_music_player as v

ROOT=Path(__file__).resolve().parents[1]
SET,VSYNC=0x0810B22C,0x0810B438
GLOBAL,TABLE,IO,VCOUNT=0x03007FF0,0x08A675D4,0x04000000,0x04000006
MAGIC=0x68736D53
MASK=0xFFFFFFFF
SOUND=v.E+0x2000
RANGES=[(SET,0x0810B2AA),(VSYNC,0x0810B466)]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
EXPECTED={i.address for a,b in RANGES for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}
LOCKS=[MAGIC,MAGIC+1,MAGIC+10,0,9,MASK]
CLOCKS=[[159,159,160,0,158,159],[0,159],[158,158,159]]
LONG_CLOCKS=[[159,160,159],[0,0,159],[159]*32+[0]+[0]*32+[159],
             [255,255,159],[159,228,227,0,158,159],[0,159],[159,159,158,159]]


def variants(cases):
    guards=[(1,MAGIC,CLOCKS[0]),(12,MAGIC+10,CLOCKS[1]),
            (0,0,CLOCKS[2]),(13,9,CLOCKS[0]),(14,MASK,CLOCKS[1]),(15,MAGIC+1,CLOCKS[2])]
    for seed,(index,lock,clock)in enumerate(guards):
        yield dict(route='guards',seed=seed,index=index,mode=index<<16,lock=lock,clock=clock)
    for index in range(16):
        for j,lock in enumerate(LOCKS):
            for k,clock in enumerate(CLOCKS):
                yield dict(route='mode_lock_clock',seed=index*18+j*3+k,index=index,mode=index<<16,lock=lock,clock=clock)
    for bit in [n for n in range(32)if not 16<=n<20]:
        for index in [1,12]:
            for high in [False,True]:
                mode=((MASK^(1<<bit))if high else(1<<bit))&~0xF0000|index<<16
                yield dict(route='ignored_mode_bits',seed=bit*4+index+int(high),index=index,mode=mode,lock=MAGIC+10,clock=CLOCKS[0])
    for placement in [v.E+0x2000,v.E+0x3000,v.E+0x10000,v.I+0x200,v.I+0x1000,v.I+0x4000]:
        for index in range(16):
            yield dict(route='placements',seed=placement+index,index=index,mode=index<<16,lock=MASK,clock=CLOCKS[1],sound=placement)
    for index in range(16):
        for j,clock in enumerate(LONG_CLOCKS):
            yield dict(route='clock_sequences',seed=index*7+j,index=index,mode=index<<16,lock=MAGIC+10,clock=clock)
    for index in range(16):
        for lock in [MAGIC,MAGIC+10]:
            yield dict(route='pointer_rebound',seed=index,index=index,mode=index<<16,lock=MAGIC+10,
                       clock=CLOCKS[0],rebound=v.I+0x2000,rebound_lock=lock)
    for index in range(16):
        for lock in [MAGIC,MAGIC+10]:
            yield dict(route='consecutive',seed=index,index=index,mode=index<<16,lock=lock,clock=CLOCKS[0],
                       second_mode=((index+1)%16)<<16,second_clock=CLOCKS[1])
    for value in range(256):
        for lock in [MAGIC,MAGIC+10]:
            yield dict(route='vsync_bytes',seed=value,target=VSYNC,mode=0,index=0,lock=lock,unknown04=value,clock=[])
    for lock in [0,1,2,8,9,10,11,MAGIC-1,MAGIC,MAGIC+1,MAGIC+9,MAGIC+10,MAGIC+11,0x7FFFFFFF,0x80000000,MASK]:
        yield dict(route='vsync_locks',seed=lock,target=VSYNC,mode=0,index=0,lock=lock,clock=[])
    rng=random.Random(0xB22CB438)
    for seed in range(cases):
        mode=rng.getrandbits(32)
        yield dict(route='random',seed=seed,index=(mode>>16)&15,mode=mode,lock=rng.getrandbits(32),
                   clock=[159]*rng.randrange(5)+[rng.choice([0,158,160,227])]*rng.randrange(1,5)+[159])


def initial(cfg):
    seed=cfg['seed']&255
    ew=bytearray(bytes((i+seed)&255 for i in range(256))*1024)
    iw=bytearray(bytes((i*13+seed)&255 for i in range(256))*128)
    image=bytearray((i*29+seed)&255 for i in range(1024))
    sound=cfg.get('sound',SOUND)
    def put(address,value,width):
        data=ew if address<v.I else iw;offset=address-(v.E if address<v.I else v.I)
        data[offset:offset+width]=(value&((1<<(8*width))-1)).to_bytes(width,'little')
    put(GLOBAL,sound,4);put(sound,cfg['lock'],4)
    put(sound+4,cfg.get('unknown04',seed),1)
    if cfg.get('rebound'):
        put(cfg['rebound'],cfg['rebound_lock'],4);put(cfg['rebound']+4,0xA5,1)
    return bytes(ew),bytes(iw),bytes(image)


def signed(word):return word if word<0x80000000 else word-0x100000000
def divide(a,b):
    a,b=signed(a&MASK),signed(b&MASK)
    if not b:return 0
    q=abs(a)//abs(b)
    return (-q if(a<0)!=(b<0)else q)&MASK


class Oracle:
    def __init__(self,cfg,images):
        self.cfg=cfg;self.data=[bytearray(x)for x in images];self.trace=[];self.clocks=self.global_reads=0
    def region(self,address,width):
        for base,data in [(v.E,self.data[0]),(v.I,self.data[1]),(IO,self.data[2]),(0x08000000,v.ROM)]:
            if base<=address and address+width<=base+len(data):return data,address-base
        raise AssertionError(('unmapped oracle',hex(address),width))
    def read(self,address,width):
        if address==GLOBAL:
            self.global_reads+=1
            if self.global_reads==2 and self.cfg.get('rebound'):
                struct.pack_into('<I',self.data[1],GLOBAL-v.I,self.cfg['rebound'])
        if address==VCOUNT:
            assert self.clocks<len(self.cfg['clock']),'oracle clock exhausted'
            self.data[2][6]=self.cfg['clock'][self.clocks];self.clocks+=1
        data,offset=self.region(address,width)
        value=int.from_bytes(data[offset:offset+width],'little')
        self.trace.append(('read',address,width,value));return value
    def write(self,address,value,width):
        value&=(1<<(8*width))-1
        data,offset=self.region(address,width);data[offset:offset+width]=value.to_bytes(width,'little')
        self.trace.append(('write',address,width,value))
    def vsync(self):
        p=self.read(GLOBAL,4);lock=self.read(p,4)
        if lock!=MAGIC:
            self.write(IO+0xC6,0xB600,2);self.write(IO+0xD2,0xB600,2)
            self.read(p+4,1);self.write(p+4,0,1);self.write(p,lock-10,4)
    def run(self):
        if self.cfg.get('target')==VSYNC:self.vsync()
        else:
            p=self.read(GLOBAL,4);index=(self.cfg['mode']>>16)&15
            self.write(p+8,index,1);samples=self.read((TABLE+2*(index-1))&MASK,2)
            self.write(p+16,samples,4);self.write(p+11,divide(1584,samples),1)
            rate=divide((597275*samples+5000)&MASK,10000)
            self.write(p+20,rate,4)
            reciprocal=signed((divide(0x1000000,rate)+1)&MASK)>>1
            self.write(p+24,reciprocal,4)
            self.write(IO+0x102,0,2);self.write(IO+0x100,-divide(280896,samples),2)
            self.vsync()
            while self.read(VCOUNT,1)==159:pass
            while self.read(VCOUNT,1)!=159:pass
            self.write(IO+0x102,0x80,2)
        assert self.clocks==len(self.cfg['clock'])
        return self.data,self.trace


def watched(address,width):
    return(v.E<=address< v.E+0x40000 or
           v.I<=address<v.I+0x8000 and not(v.I+0x7000<=address<v.I+0x7800)or
           IO<=address<IO+1024 or TABLE-2<=address<TABLE+30)


def execute(cfg,images,native,out,coverage):
    uc=v.Uc(v.UC_ARCH_ARM,v.UC_MODE_THUMB);uc.ctl_set_cpu_model(v.UC_CPU_ARM_926)
    for base,size,data in [(0x08000000,0x1000000,v.ROM),(v.E,0x40000,images[0]),(v.I,0x8000,images[1]),(IO,4096,images[2])]:
        uc.mem_map(base,size);uc.mem_write(base,bytes(data))
    trace=[];errors=[];fallbacks=[];clock=global_reads=0
    def failure(message):
        # A bad native wait loop cannot propagate a Python exception through
        # ctypes. Stop this verifier process with a diagnostic instead of hanging.
        (out/'failed_case.json').write_text(json.dumps(dict(case=cfg,error=message,native=bool(native)),indent=2)+'\n')
        print('FAIL:',message,flush=True);os._exit(1)
    def prepare(address,width):
        nonlocal clock,global_reads
        if address==GLOBAL:
            global_reads+=1
            if global_reads==2 and cfg.get('rebound'):
                uc.mem_write(GLOBAL,struct.pack('<I',cfg['rebound']))
        if address==VCOUNT:
            if clock>=len(cfg['clock']):failure('VCOUNT script exhausted; extra polling or nonterminating native loop')
            uc.mem_write(VCOUNT,bytes([cfg['clock'][clock]]));clock+=1
    def read(user,address,width):
        try:
            prepare(address,width);value=int.from_bytes(uc.mem_read(address,width),'little')
            trace.append(('read',address,width,value));return value
        except Exception as exc:errors.append(repr(exc));return 0
    def write(user,address,value,width):
        value&=(1<<(8*width))-1
        trace.append(('write',address,width,value))
        try:uc.mem_write(address,value.to_bytes(width,'little'))
        except Exception as exc:errors.append(repr(exc))
    def call(user,target,a0,a1,a2):
        fallbacks.append(target);return 0
    saved=[0xA0B00000+i for i in range(8)];stack=v.I+0x7800
    for reg,value in zip(v.REGS[4:],saved):uc.reg_write(reg,value)
    uc.reg_write(v.UC_ARM_REG_SP,stack)
    if native:
        host=v.Host(None,v.READ(read),v.WRITE(write),v.CALL(call))
        fn=native.Dbaa_AudioCall;fn.argtypes=[ctypes.POINTER(v.Host),*[ctypes.c_uint32]*4];fn.restype=ctypes.c_uint32
        fn(ctypes.byref(host),cfg.get('target',SET)|(cfg['seed']&1),cfg['mode'],cfg.get('a1',0),cfg.get('a2',0))
    else:
        if cfg.get('model_cpuset_fill32') or cfg.get('model_cpuset_copy32'):
            def on_interrupt(machine,number,data):
                pc=machine.reg_read(v.UC_ARM_REG_PC)
                assert number==2 and pc==0x08115A8A,('unexpected interrupt',number,hex(pc))
                source,destination,control=[machine.reg_read(r)for r in v.REGS[:3]]
                assert not(source&3 or destination&3)
                if control==0x04000100 and cfg.get('model_cpuset_copy32'):
                    assert source==0x0810A108 and destination==0x030008B0
                    cfg['cpuset_calls'].append(dict(source=source,destination=destination,control=control))
                    for offset in range(0,1024,4):
                        value=int.from_bytes(machine.mem_read(source+offset,4),'little')
                        if watched(source+offset,4):trace.append(('read',source+offset,4,value))
                        machine.mem_write(destination+offset,value.to_bytes(4,'little'))
                        if watched(destination+offset,4):trace.append(('write',destination+offset,4,value))
                    return
                assert control in (0x05000318,0x050003EC,0x05000040) and cfg.get('model_cpuset_fill32')
                value=int.from_bytes(machine.mem_read(source,4),'little')
                assert value==0
                cfg['cpuset_calls'].append(dict(destination=destination,control=control,value=value))
                for offset in range(0,(control&0x1FFFFF)*4,4):
                    machine.mem_write(destination+offset,value.to_bytes(4,'little'))
                    if watched(destination+offset,4):trace.append(('write',destination+offset,4,value))
            uc.hook_add(UC_HOOK_INTR,on_interrupt)
        def on_read(machine,access,address,width,value,data):
            if watched(address,width):
                prepare(address,width)
                trace.append(('read',address,width,int.from_bytes(machine.mem_read(address,width),'little')))
        def on_write(machine,access,address,width,value,data):
            if watched(address,width):trace.append(('write',address,width,value&((1<<(8*width))-1)))
        def on_code(machine,address,size,data):
            if cfg.get('ram_code_map'):
                base,source,length=cfg['ram_code_map']
                if base<=address<base+length:address=source+address-base
            if address in EXPECTED:coverage.add(address)
        uc.hook_add(v.UC_HOOK_MEM_READ,on_read);uc.hook_add(v.UC_HOOK_MEM_WRITE,on_write);uc.hook_add(v.UC_HOOK_CODE,on_code)
        uc.reg_write(v.UC_ARM_REG_R0,cfg['mode']);uc.reg_write(v.UC_ARM_REG_R1,cfg.get('a1',0))
        uc.reg_write(v.UC_ARM_REG_R2,cfg.get('a2',0));uc.reg_write(v.UC_ARM_REG_LR,v.STOP+1)
        uc.emu_start(cfg.get('target',SET)|1,v.STOP,count=cfg.get('instruction_limit',300000))
        assert uc.reg_read(v.UC_ARM_REG_PC)==v.STOP,'ARM instruction limit'
    assert not errors and not fallbacks,(errors,fallbacks)
    assert uc.reg_read(v.UC_ARM_REG_SP)==stack and[uc.reg_read(r)for r in v.REGS[4:]]==saved
    assert clock==len(cfg['clock']),'VCOUNT poll count differs'
    data=[bytes(uc.mem_read(v.E,0x40000)),bytes(uc.mem_read(v.I,0x8000)),bytes(uc.mem_read(IO,1024))]
    return data,trace,global_reads


def comparable(images):
    return bytes(images[0])+bytes(images[1][:0x7000])+bytes(images[1][0x7800:])+bytes(images[2])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_sound_frequency_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    v.OUT=out;v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();dll=v.build_native()
    counts={};coverage=set();digest=hashlib.sha256();executions=polls=io_writes=sequences=0
    for number,cfg in enumerate(variants(args.cases)):
        images=initial(cfg)
        steps=[cfg]
        if cfg['route']=='consecutive':
            steps.append(dict(cfg,mode=cfg['second_mode'],clock=cfg['second_clock']));sequences+=1
        rom_trace=native_trace=expected_trace=None
        try:
            for step in steps:
                oracle=Oracle(step,images);wanted,expected_trace=oracle.run()
                original,rom_trace,rom_ptr_reads=execute(step,images,None,out,coverage)
                candidate,native_trace,native_ptr_reads=execute(step,images,dll,out,coverage)
                assert comparable(original)==comparable(candidate)==comparable(wanted),'RAM or flat I/O images differ'
                assert rom_trace==native_trace==expected_trace,'ordered data read/write trace differs'
                assert rom_ptr_reads==native_ptr_reads==oracle.global_reads,'global sound pointer read count differs'
                executions+=1;polls+=len(step['clock'])
                io_writes+=sum(row[0]=='write'and IO<=row[1]<IO+1024 for row in rom_trace)
                digest.update(comparable(original));digest.update(json.dumps(rom_trace).encode())
                # Carry only game state; dead ARM stack bytes have no host-C counterpart.
                original[1]=bytes(original[1][:0x7000])+bytes(images[1][0x7000:0x7800])+bytes(original[1][0x7800:])
                images=original
        except Exception as exc:
            failure=dict(case=cfg,error=repr(exc))
            if rom_trace is not None:failure.update(rom_trace=rom_trace,native_trace=native_trace,expected_trace=expected_trace)
            (out/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',cfg['route'],cfg['seed'],repr(exc),flush=True);return 1
        counts[cfg['route']]=counts.get(cfg['route'],0)+1
        if number%256==0:print('Passed sound frequency cases:',number+1,flush=True)
    assert coverage==EXPECTED
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,executions=executions,
        consecutive_sequences=sequences,observed_vcount_reads=polls,observed_io_writes=io_writes,
        all_ram_equal=True,io_images_equal=True,ordered_reads_and_writes_equal=True,independent_model_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        frequency_instructions_covered=sum(a<=p<b for p in coverage for a,b in RANGES[:1]),
        vsync_instructions_covered=sum(a<=p<b for p in coverage for a,b in RANGES[1:]),
        frequency_mode_nibbles_tested=16,documented_modes=list(range(1,13)),unsupported_modes_observed=[0,13,14,15],
        table_halfwords=[struct.unpack_from('<H',v.ROM,TABLE-0x08000000+2*(i-1))[0]for i in range(16)],
        mode_mask_ignored_bits_verified=True,signed_division_and_32bit_multiply_wrap_verified=True,
        reciprocal_arithmetic_shift_verified=True,timer_halfword_width_and_order_verified=True,
        leave_then_enter_vcount_verified=True,vsync_magic_guard_and_lock_wrap_verified=True,
        volatile_unknown04_read_verified=True,sound_pointer_reread_verified=True,
        original_callee_saved_registers_preserved=True,native_new_services_fallback_to_arm=False,arm_fallback_targets=[],
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        native_dll_sha256=sha(out/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),
        host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),rom_sha1=expected,results_sha256=digest.hexdigest(),
        io_model='flat I/O mirror and scripted VCOUNT bus reads; hardware side effects and real time are not emulated',
        hardware_register_side_effects_validated=False,real_time_validated=False,audible_output_validated=False,
        byte_matching=False,full_game_boot=False,cpu='Unicorn ARM926; functional comparison, not GBA cycles')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'sound frequency cases;',executions,'executions;',polls,'VCOUNT reads;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
