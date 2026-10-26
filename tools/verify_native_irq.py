"""Original relocated ARM IRQ dispatcher versus native C selection and data bus."""
from pathlib import Path
import argparse,ctypes,hashlib,json,random,struct,subprocess,sys
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
import verify_music_player as v

ROOT=Path(__file__).resolve().parents[1]
BASE,IO,TABLE,CALLBACK=0x03001F50,0x04000000,0x03001F10,0x0203F000
ROM=(ROOT/'baserom.gba').read_bytes()
class Selection(ctypes.Structure):
    _fields_=[(n,ctypes.c_uint32)for n in['target','table_address','table_offset','acknowledged']]


def execute(ie,flags,native,coverage):
    uc=Uc(UC_ARCH_ARM,UC_MODE_ARM);uc.ctl_set_cpu_model(UC_CPU_ARM_926)
    for a,n in[(0x02000000,0x40000),(0x03000000,0x8000),(IO,0x1000)]:
        uc.mem_map(a,n)
    uc.mem_write(BASE,ROM[0xFC:0x2FC])
    uc.mem_write(TABLE,struct.pack('<15I',*[CALLBACK+4*i+1 for i in range(15)]))
    uc.mem_write(IO+0x200,struct.pack('<HH',ie,flags))
    trace=[]
    def read(user,a,n):
        value=int.from_bytes(uc.mem_read(a,n),'little')
        trace.append(('read',a,n,value));return value
    def write(user,a,value,n):
        value&=(1<<(n*8))-1;trace.append(('write',a,n,value))
        if a==IO+0x202:
            value=int.from_bytes(uc.mem_read(a,n),'little')&~value
        uc.mem_write(a,value.to_bytes(n,'little'))
    initial=[0xC0FF0000+i for i in range(15)]
    for i,value in enumerate(initial):uc.reg_write(UC_ARM_REG_R0+i,value)
    # Set V=1 to ensure that the selector preserves it; its first rotated
    # ANDS clears C irrespective of the incoming C flag.
    uc.reg_write(UC_ARM_REG_CPSR,0xB000001F)
    if native:
        host=v.Host(None,v.READ(read),v.WRITE(write),v.CALL(lambda *args:0))
        selected=Selection()
        panic=native.Dbaa_IrqSelect(ctypes.byref(host),BASE,ctypes.byref(selected))
        result=dict(panic=bool(panic))
        if not panic:result.update(registers=[selected.target,selected.table_address,selected.table_offset,IO+0x200],
            flags=(0,not bool(selected.acknowledged),0,1))
    else:
        result={}
        def on_code(machine,a,n,user):
            if BASE<=a<BASE+0xC4:coverage.add(a-BASE+0x080000FC)
            if a==BASE+0x18 and machine.reg_read(UC_ARM_REG_R0):
                result['panic']=True;machine.emu_stop()
            if CALLBACK<=a<CALLBACK+60:
                result.update(panic=False,registers=[machine.reg_read(UC_ARM_REG_R0+i)for i in range(4)])
                cpsr=machine.reg_read(UC_ARM_REG_CPSR)
                result['flags']=tuple(bool(cpsr&(1<<bit))for bit in[31,30,29,28]);machine.emu_stop()
        def on_read(machine,access,a,n,value,user):
            trace.append(('read',a,n,int.from_bytes(machine.mem_read(a,n),'little')))
        def on_write(machine,access,a,n,value,user):
            trace.append(('write',a,n,value&((1<<(8*n))-1)))
            # Apply W1C after STRH, at the callback entry, rather than inside
            # Unicorn's pre-store hook (the CPU store would overwrite it).
        uc.hook_add(UC_HOOK_CODE,on_code);uc.hook_add(UC_HOOK_MEM_READ,on_read)
        uc.hook_add(UC_HOOK_MEM_WRITE,on_write)
        uc.emu_start(BASE,0,count=128)
        assert result,('IRQ failed to reach callback/panic',hex(ie),hex(flags))
        assert[uc.reg_read(UC_ARM_REG_R0+i)for i in range(4,15)]==initial[4:]
        if not result['panic']:
            ack=next(x[3]for x in trace if x[0]=='write')
            uc.mem_write(IO+0x202,struct.pack('<H',flags&~ack))
    return result,trace,bytes(uc.mem_read(IO,1024))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-dir',type=Path,default=ROOT/'build/native_irq_validation')
    p.add_argument('--source',type=Path,default=ROOT/'port/native/irq_dispatch.c');p.add_argument('--quick',action='store_true')
    a=p.parse_args(argv);out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    command=[str(v.HOST_GCC),'-std=c99','-O2','-Wall','-Wextra','-Werror','-shared',
        '-I'+str(ROOT/'port/include'),'-I'+str(ROOT/'port/native'),str(a.source.resolve()),'-o',str(out/'irq.dll')]
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (out/'build.log').write_text(json.dumps(command)+'\n'+r.stdout+r.stderr)
    if r.returncode:print(r.stderr);return 1
    dll=ctypes.CDLL(str(out/'irq.dll'));dll.Dbaa_IrqSelect.argtypes=[ctypes.POINTER(v.Host),ctypes.c_uint32,ctypes.POINTER(Selection)]
    dll.Dbaa_IrqSelect.restype=ctypes.c_int;coverage=set();digest=hashlib.sha256()
    cases=[(0xFFFF,x)for x in(range(0x10000)if not a.quick else[0,1,2,4,8,16,32,64,128,192,256,512,1024,2048,4096,8192,16384,32768,65535])]
    rng=random.Random(0x80000FC)
    cases +=[(rng.randrange(65536),rng.randrange(65536))for _ in range(32 if a.quick else 1024)]
    try:
        for number,(ie,flags)in enumerate(cases):
            ref=execute(ie,flags,None,coverage);other=execute(ie,flags,dll,set())
            assert ref==other,dict(ie=ie,flags=flags,rom=ref[:2],native=other[:2])
            digest.update(repr(ref[:2]).encode());digest.update(ref[2])
            if number%8192==0:print('Passed IRQ cases:',number+1,flush=True)
        assert len(coverage)==49,(len(coverage),[hex(x)for x in coverage])
        report=dict(cases=len(cases),quick=a.quick,original_irq_instructions=len(coverage),rom_register_context_equal=True,
            ordered_data_bus_equal=True,io_equal=True,gamepak_panic_detected=True,byte_matching=False,
            native_arm_execution=False,rom_sha1=hashlib.sha1(ROM).hexdigest(),source_sha256=sha(a.source),
            header_sha256=sha(ROOT/'port/native/irq_dispatch.h'),compiler_sha256=sha(v.HOST_GCC),
            tool_sha256=sha(__file__),native_dll_sha256=sha(out/'irq.dll'),results_sha256=digest.hexdigest())
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS IRQ:',len(cases),'cases;',len(coverage),'original ARM instructions');return 0
    except Exception as e:
        (out/'failed_case.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n')
        print('FAIL',repr(e));return 1
if __name__=='__main__':raise SystemExit(main())
