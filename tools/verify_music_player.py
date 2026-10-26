"""Compare native Windows C with the isolated ROM routine (not a full GBA boot).

Install requirements-validation.txt and the matching toolchain first. Synthetic
callbacks exercise the player independently of the remaining audio engine.
"""
from pathlib import Path
import argparse, ctypes, hashlib, json, random, struct, subprocess, sys
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *

ROOT = Path(__file__).resolve().parents[1]
ROM = (ROOT/'baserom.gba').read_bytes()
OUT = ROOT/'build/native_music_validation'
COVERAGE = set()
CALLBACKS = set()
FALLBACK_TARGETS = set()
NATIVE_AUDIO_TARGETS = {0x0810A084, 0x0810A724, 0x0810A4AC, 0x0810A4C4, 0x0810A4E4, 0x0810A514, 0x0810A548, 0x0810A554, 0x0810A574, 0x0810A590, 0x0810A5A4, 0x0810A5D4, 0x0810A5E0, 0x0810A5F4, 0x0810A608, 0x0810A638, 0x0810A64C, 0x0810A660, 0x0810A674, 0x0810A688, 0x0810A694, 0x0810A6AC, 0x0810A6C0, 0x0810A98C, 0x0810AA00, 0x0810AC00, 0x0810AC40, 0x0810AC5C, 0x0810AC68, 0x0810AC7C, 0x0810AC90, 0x0810AFF0, 0x0810B10C, 0x0810B120, 0x0810B134, 0x0810B22C, 0x0810B2D0, 0x0810B3BC, 0x0810B438, 0x0810B610, 0x0810B6D8, 0x0810B78C, 0x0810B834, 0x0810B884, 0x0810B8EC, 0x0810BFAC, 0x0810C104, 0x0810C124, 0x0810C138, 0x0810C180, 0x0810C194, 0x0810C1A8, 0x0810C1BC, 0x0810C1D0, 0x0810C1E4, 0x0810C1F0, 0x0810C1FC, 0x0810C210, 0x0810C224}
NATIVE_AUDIO_TARGETS |= {0x0810AD34, 0x0810ADAC, 0x0810B474}
NATIVE_AUDIO_TARGETS |= {0x0810ADB8, 0x0810AEEC, 0x0810B4EC, 0x0810B5D0}
NATIVE = None
HOST_SOURCE = ROOT/'port/audio/music_player_update.c'
HOST_HELPERS_SOURCE = ROOT/'port/audio/audio_helpers.c'
HOST_GCC = ROOT/'tools/local/w64devkit/bin/gcc.exe'
START, STOP = 0x0810A724, 0x08010300
E, I = 0x02000000, 0x03000000
PLAYER, TRACKS, CHANNELS, COMMANDS, WAVE = E+0x100, E+0x1000, E+0x3000, E+0x10000, E+0x20000
SOUND, NEXT, NOTE, STOPCGB, TABLE = I, 0x08010000, 0x08010004, 0x08010200, I+0x4000
FREQUENCY = 0x08010204
REGS = [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
        UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
        UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]

def u32(data, off): return struct.unpack_from('<I', data, off)[0]
def w32(data, off, v): struct.pack_into('<I', data, off, v & 0xffffffff)
def w16(data, off, v): struct.pack_into('<H', data, off, v & 65535)
def build_native():
    output=OUT/'music_player_native.dll'
    flags=['-std=c99','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'port/include'),'-shared']
    command=[str(HOST_GCC),*flags,str(HOST_SOURCE),str(HOST_HELPERS_SOURCE),'-o',str(output)]
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    if r.returncode:raise ValueError(r.stderr)
    (OUT/'build.log').write_text(json.dumps(command)+'\n'+r.stdout+r.stderr)
    return ctypes.CDLL(str(output))

READ=ctypes.CFUNCTYPE(ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32)
WRITE=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32)
CALL=ctypes.CFUNCTYPE(ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32)
class Host(ctypes.Structure):
    _fields_=[('user',ctypes.c_void_p),('read',READ),('write',WRITE),('call',CALL)]

def fixture(seed):
    rng=random.Random(seed)
    ew=bytearray(0x40000);iw=bytearray(0x8000)
    count=rng.randrange(9)
    p=PLAYER-E
    w32(ew,p+4,rng.choice([0,1,7,0x80000000]))
    ew[p+8]=count
    w32(ew,p+12,rng.getrandbits(32))
    w16(ew,p+0x20,rng.choice([0,1,75,149,150,151,300,65535]))
    w16(ew,p+0x22,rng.choice([0,1,149,150,65535]))
    w16(ew,p+0x24,rng.choice([0,0,0,1,3]))
    w16(ew,p+0x26,rng.choice([0,1,2,65535]))
    w16(ew,p+0x28,rng.choice([0,1,3,16,128,255,256,0x8000,0xffff]))
    w32(ew,p+0x2c,TRACKS)
    w32(ew,p+0x34,rng.choice([0,0x68736d52,0x68736d53,0x68736d53,0x68736d53]))
    w32(ew,p+0x38,rng.choice([0,NEXT+1]))
    w32(ew,p+0x3c,E+0x500)
    w32(ew,WAVE-E+4,0x00400000)
    for index in range(9):
        t=TRACKS-E+index*80
        ew[t:t+80]=bytes(rng.randrange(256) for _ in range(80))
        ew[t]=rng.choice([0,0x80,0x81,0x83,0x84,0x8c,0x8f,0xc0])
        ew[t+1]=rng.choice([0,1,2,255])
        ew[t+7]=rng.choice([0xbd,0xcf])
        ew[t+0x19]=rng.choice([0,1,22,63,64,127,255])
        ew[t+0x17]=rng.choice([0,1,127,255])
        ew[t+0x1c]=rng.choice([0,0,1,255])
        cp=COMMANDS+index*256
        w32(ew,t+0x40,cp)
        patterns=[bytes([0x81,0x82,0xb1]),bytes([0xb1+seed%30,32,0x81,0xb1]),
                  bytes([0xcf+seed%49,50,0x81,0xb1]),bytes([40,0x81,0xb1]),
                  bytes([0x80,0x81,0xb1]),bytes([0xb2,37,0xb1])]
        pattern=rng.choice(patterns)
        ew[cp-E:cp-E+len(pattern)]=pattern
        n=rng.randrange(4)
        w32(ew,t+0x20,CHANNELS+index*0x100 if n else 0)
        for j in range(n):
            c=CHANNELS-E+index*0x100+j*64
            ew[c:c+64]=bytes(rng.randrange(256) for _ in range(64))
            ew[c]=rng.choice([0,1,4,0x10,0x40,0x80,0xc7])
            ew[c+1]=rng.randrange(5)
            ew[c+0x10]=rng.choice([0,1,2,255])
            w32(ew,c+0x24,WAVE)
            w32(ew,c+0x2c,TRACKS+index*80)
            w32(ew,c+0x30,CHANNELS+index*0x100+(j-1)*64 if j else 0)
            w32(ew,c+0x34,CHANNELS+index*0x100+(j+1)*64 if j+1<n else 0)
    w32(iw,0x7ff0,SOUND)
    w32(iw,0,0x68736d53)
    w32(iw,0x18,0x00100000)
    w32(iw,0x2c,STOPCGB+1)
    w32(iw,0x30,0x0810B78D)
    w32(iw,0x34,TABLE)
    w32(iw,0x38,NOTE+1)
    w32(iw,0x1cfc,0x0810A4AD)
    # Sound_ClearChannelChain's RAM callback, installed by Sound_Initialize.
    callback_slot=u32(ROM,0x10B11C)
    w32(iw,callback_slot-I,0x0810A4C5)
    for index in range(30):w32(iw,TABLE-I+4*index,0x08010101+4*index)
    if seed>=10000:
        index=seed-10000
        w32(ew,p+4,0);ew[p+8]=1
        w32(ew,p+0x34,0x68736d53)
        w16(ew,p+0x20,150);w16(ew,p+0x22,0);w16(ew,p+0x24,0)
        t=TRACKS-E;ew[t]=0x80;ew[t+1]=0
        opcode=0xb1+index if index<30 else 0xcf+index-30 if index<79 else 0x80+index-79
        pattern=bytes([opcode,50,0x81,0xb1]) if index<79 else bytes([opcode,0x81,0xb1])
        ew[COMMANDS-E:COMMANDS-E+len(pattern)]=pattern
    return bytes(ew),bytes(iw)

def execute(initial,candidate=None,routine=None):
    uc=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
    uc.ctl_set_cpu_model(UC_CPU_ARM_926)
    uc.mem_map(0x08000000,0x1000000);uc.mem_write(0x08000000,ROM)
    uc.mem_map(E,0x40000);uc.mem_write(E,bytes(initial[0]))
    uc.mem_map(I,0x8000);uc.mem_write(I,bytes(initial[1]))
    if routine:
        for address,contents in routine.get('extra_memory',[]):
            base=address & ~4095
            size=(address-base+len(contents)+4095)&~4095
            uc.mem_map(base,size);uc.mem_write(address,contents)

    initial_regs=[0x12340000+4*i for i in range(12)]
    for reg,val in zip(REGS,initial_regs):uc.reg_write(reg,val)
    uc.reg_write(UC_ARM_REG_R0,PLAYER)
    uc.reg_write(UC_ARM_REG_SP,I+0x7800);uc.reg_write(UC_ARM_REG_LR,STOP+1)
    trace=[]
    watched_write_addresses=set(routine.get('observe_writes',[]))if routine else set()
    def rd(addr,n=4):return int.from_bytes(uc.mem_read(addr,n),'little')
    def wr(addr,v,n=4):uc.mem_write(addr,(v&((1<<(8*n))-1)).to_bytes(n,'little'))
    def callback(machine,address,size,data):
        if address==STOP:
            machine.emu_stop();return
        args=[machine.reg_read(r) for r in REGS[:3]]
        result = None
        if address==NEXT:
            trace.append(('next',args[0],rd(PLAYER+0x34)))
            wr(args[0],rd(args[0])+1)
        elif address==NOTE:
            opcode,player,track=args
            trace.append(('note',opcode,player,track,rd(track+0x40)))
            CALLBACKS.add(('note',opcode))
            ptr=rd(track+0x40)
            wr(track+5,rd(ptr,1),1);wr(track+0x40,ptr+1);wr(track+1,1,1)
        elif address==STOPCGB:
            trace.append(('stop_cgb',args[0]&255))
        elif address==FREQUENCY:
            trace.append(('frequency',*args))
            result=(args[0]*0x1000000+args[1]*257+args[2])&0xffffffff
        elif 0x08010100<=address<0x08010178 and address%4==0:
            index=(address-0x08010100)//4
            player,track=args[:2]
            trace.append(('command',index,player,track,rd(track+0x40)))
            CALLBACKS.add(('command',index))
            if index==0:wr(track,0,1)
            else:
                ptr=rd(track+0x40)
                wr(track+0x12,rd(ptr,1),1);wr(track+0x40,ptr+1)
        else:raise AssertionError(('unexpected callback',hex(address)))
        for index,reg in enumerate(REGS[:4]):machine.reg_write(reg,0xAAAA0000+index)
        if result is not None:machine.reg_write(UC_ARM_REG_R0,result)
        machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE,callback,begin=NEXT,end=STOP)
    errors=[]
    def invoke(target,a0,a1=0,a2=0,a3=0):
        for reg,value in zip(REGS[:4],[a0,a1,a2,a3]):uc.reg_write(reg,value)
        uc.reg_write(UC_ARM_REG_LR,STOP+1)
        uc.emu_start(target|1,STOP,count=200000)
        assert uc.reg_read(UC_ARM_REG_PC)==STOP,('instruction limit',hex(uc.reg_read(UC_ARM_REG_PC)))
        assert uc.reg_read(UC_ARM_REG_SP)==I+0x7800
        return uc.reg_read(UC_ARM_REG_R0)
    if candidate:
        def native_read(user,address,width):
            if routine and address in routine.get('observe_reads',[]):
                trace.append(('read',address,width))
            try:return rd(address,width)
            except Exception as e:errors.append(str(e));return 0
        def native_write(user,address,value,width):
            if address in watched_write_addresses:
                trace.append(('write',address,width,value&((1<<(8*width))-1)))
            try:wr(address,value,width)
            except Exception as e:errors.append(str(e))
        def native_call(user,target,a0,a1,a2):
            FALLBACK_TARGETS.add(target & ~1)
            try:return invoke(target,a0,a1,a2)
            except Exception as e:errors.append(str(e));return 0
        host=Host(None,READ(native_read),WRITE(native_write),CALL(native_call))
        name=routine['native_name'] if routine else 'Dbaa_MusicPlayerUpdate'
        arguments=routine['native_args'] if routine else [PLAYER]
        fn=getattr(NATIVE,name)
        fn.argtypes=[ctypes.POINTER(Host),*[ctypes.c_uint32]*len(arguments)]
        fn.restype=ctypes.c_uint32 if routine and routine.get('compare_return') else None
        result=fn(ctypes.byref(host),*arguments)
        assert not errors,errors
        assert not FALLBACK_TARGETS & NATIVE_AUDIO_TARGETS,('native helper delegated to ARM',FALLBACK_TARGETS & NATIVE_AUDIO_TARGETS)
    else:
        if routine and routine.get('observe_writes'):
            def observe_write(machine,access,address,size,value,data):
                if address in watched_write_addresses:trace.append(('write',address,size,value&((1<<(8*size))-1)))
            uc.hook_add(UC_HOOK_MEM_WRITE,observe_write)
        if routine and routine.get('observe_reads'):
            watched=set(routine['observe_reads'])
            def observe_read(machine,access,address,size,value,data):
                if address in watched:trace.append(('read',address,size))
            uc.hook_add(UC_HOOK_MEM_READ,observe_read)
        cover_start=routine.get('cover_start',routine['address']) if routine else START
        cover_end=routine['cover_end'] if routine else 0x0810A97C
        uc.hook_add(UC_HOOK_CODE,lambda machine,address,size,data:COVERAGE.add(address),begin=cover_start,end=cover_end)
        invoke(routine['address'],*routine['arm_args']) if routine else invoke(START,PLAYER)
        result=uc.reg_read(REGS[routine.get('result_register',0)]) if routine and routine.get('compare_return') else None
    assert [uc.reg_read(r) for r in REGS[4:]]==initial_regs[4:]
    # ARM stack spill bytes have no native-C counterpart. Exclude that dead
    # stack region; compare game RAM and callback effects in both executions.
    memory=bytes(uc.mem_read(E,0x40000))+bytes(uc.mem_read(I,0x7000))+bytes(uc.mem_read(I+0x7800,0x800))
    if routine:
        for address,contents in routine.get('extra_memory',[]):
            memory+=bytes(uc.mem_read(address,len(contents)))
    return (memory,trace,result) if routine else (memory,trace)

def main(argv=None):
    global OUT,NATIVE,HOST_SOURCE,HOST_HELPERS_SOURCE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=1000)
    parser.add_argument('--out-dir',type=Path,default=OUT)
    parser.add_argument('--source',type=Path,default=HOST_SOURCE)
    parser.add_argument('--helpers-source',type=Path,default=HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases < 0:
        parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(ROM).hexdigest()!=expected:
        parser.error('requires the exact configured USA ROM SHA-1')
    OUT=args.out_dir.resolve();OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'report.json').unlink(missing_ok=True)
    (OUT/'failed_seed.json').unlink(missing_ok=True)
    HOST_SOURCE=args.source.resolve()
    HOST_HELPERS_SOURCE=args.helpers_source.resolve()
    NATIVE=build_native()
    seeds=[*range(args.cases),*range(10000,10128)]
    for number,seed in enumerate(seeds):
        initial=fixture(seed)
        ref=execute(initial)
        other=execute(initial,True)
        if ref!=other:
            diff=[i for i,(a,b) in enumerate(zip(ref[0],other[0])) if a!=b]
            print('FAIL seed:',seed,'memory diffs:',diff[:12],flush=True)
            print('trace ROM:',ref[1]);print('trace C:',other[1])
            (OUT/'failed_seed.json').write_text(json.dumps(dict(seed=seed,differences=diff,rom_trace=ref[1],c_trace=other[1]),indent=2)+'\n')
            return 1
        if number%100==0:print('Passed',number+1,'cases',flush=True)
    command_indices=sorted(index for kind,index in CALLBACKS if kind=='command')
    note_indices=sorted(index for kind,index in CALLBACKS if kind=='note')
    assert command_indices==list(range(30)),command_indices
    assert note_indices==list(range(49)),note_indices
    report=dict(cases=len(seeds),randomized_cases=args.cases,forced_cases=128,source=str(HOST_SOURCE.relative_to(ROOT)) if HOST_SOURCE.is_relative_to(ROOT) else str(HOST_SOURCE),
        source_sha256=hashlib.sha256(HOST_SOURCE.read_bytes()).hexdigest(),
        header_sha256=hashlib.sha256((ROOT/'port/include/music_player.h').read_bytes()).hexdigest(),
        native_sources_sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HOST_SOURCE,HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        compiler_sha256=hashlib.sha256(HOST_GCC.read_bytes()).hexdigest(),
        native_dll_sha256=hashlib.sha256((OUT/'music_player_native.dll').read_bytes()).hexdigest(),
        rom_sha1=hashlib.sha1(ROM).hexdigest(),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
        cpu='Unicorn ARM926 (functional Thumb subset; not ARM7 cycle emulation)',
        scope=f'isolated routine; {len(NATIVE_AUDIO_TARGETS)} bound audio entry addresses; synthetic notes/commands/next-player/CGB-stop callbacks',
        full_game_boot=False,byte_matching=False,all_ram_equal=True,callback_traces_equal=True,
        command_indices=command_indices,note_indices=note_indices,original_instructions_covered=len(COVERAGE),
        native_audio_targets=sorted(NATIVE_AUDIO_TARGETS),arm_fallback_targets=sorted(FALLBACK_TARGETS),
        original_instruction_addresses=[hex(a) for a in sorted(COVERAGE)])
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',len(seeds),'native Windows C / original ARM differential cases; NOT a byte matching result.')
    return 0

if __name__=='__main__':raise SystemExit(main())
