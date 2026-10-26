"""Compare native mode configuration and VSync-off with ROM and a state oracle.

The original SWI CpuSet uses a controlled fill32 service model, not a BIOS image.
MMIO is a flat mirror with scripted VCOUNT; no DMA/FIFO effects or real time.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_sound_frequency as f
import verify_music_player as v

ROOT=Path(__file__).resolve().parents[1]
MODE,OFF=0x0810B2D0,0x0810B3BC
NEW_RANGES=[(MODE,0x0810B35C),(OFF,0x0810B41A)]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
NEW={i.address for a,b in NEW_RANGES for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}
EXPECTED=f.EXPECTED|NEW
LOCKS=[0,1,9,10,f.MAGIC-1,f.MAGIC,f.MAGIC+1,f.MAGIC+2,f.MAGIC+9,
       f.MAGIC+10,f.MAGIC+11,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF,0x100]
DMA_WORDS=[0,0x02000000,0xFFFFFFFF,0x7DFFFFFF,0x80000000,0x82000004]


def case(route,seed,mode=0,lock=f.MAGIC,target=MODE,**extra):
    cfg=dict(route=route,seed=seed,mode=mode,lock=lock,target=target,dma1=0xA5120037&~0x02000000,
             dma2=0x5B34007D|0x02000000,bias=0xFF)
    cfg.update(extra)
    cfg['clock']=f.CLOCKS[seed%3]if target==MODE and lock==f.MAGIC and mode&0xF0000 else[]
    return cfg


def variants(cases):
    for seed,(mode,lock,target)in enumerate([(0,f.MAGIC,MODE),(0x00800080,f.MAGIC,MODE),
        (0x001234FF,f.MAGIC,MODE),(0x00FF0F80,f.MAGIC,MODE),(0xFFFFFFFF,f.MAGIC+1,MODE),
        (0,f.MAGIC,OFF),(0,f.MAGIC+1,OFF),(0,f.MAGIC+10,OFF)]):
        yield case('guards',seed,mode,lock,target)
    for value in range(256):yield case('reverb_bytes',value,value)
    for count in range(16):yield case('channel_counts',count,count<<8)
    for volume in range(16):yield case('volumes',volume,volume<<12)
    for flags in range(16):
        for bias in [0,1,63,64,128,255]:yield case('bias_flags',flags*256+bias,flags<<20,bias=bias)
    for bias in range(256):
        for flags in [8,3]:yield case('bias_bytes',bias*16+flags,flags<<20,bias=bias)
    for index in range(16):
        for flags in range(4):
            yield case('frequencies',index*4+flags,index<<16,dma1=0xA5120037&~0x02000000|(flags&1)<<25,
                       dma2=0x5934007D&~0x02000000|((flags>>1)&1)<<25)
    for bit in [22,*range(24,32)]:
        for mode in [0,0x00123480,0x00BF5F7F,0x00800000]:
            yield case('ignored_bits',bit*16+(mode&15),mode^(1<<bit))
    for lock in LOCKS:
        for flags in range(4):
            yield case('off_locks',lock*4+flags,lock=lock,target=OFF,
                       dma1=(flags&1)<<25,dma2=((flags>>1)&1)<<25)
    for first in DMA_WORDS:
        for second in DMA_WORDS:
            yield case('dma_words',first^second,lock=f.MAGIC+1,target=OFF,dma1=first,dma2=second)
    for sound in [v.E+0x2000,v.E+0x3000,v.E+0x10000,v.I+0x200,v.I+0x1000,v.I+0x4000]:
        for target,lock in [(MODE,f.MAGIC),(OFF,f.MAGIC),(OFF,f.MAGIC+1)]:
            yield case('placements',sound,0x00BF5FFF,lock,target,sound=sound)
    for index in range(16):
        for lock in [f.MAGIC,f.MAGIC+1,f.MAGIC+10]:
            yield case('pointer_rebound',index*3+lock%3,index<<16,rebound=v.I+0x2000,rebound_lock=lock)
    for index in range(16):
        for flags in range(2):
            yield case('stop_resume_reconfigure',index*2+flags,index<<16,
                       second_mode=(((index+1)%15+1)<<16)|0x00A03580,dma1=flags<<25,dma2=(1-flags)<<25)
    rng=random.Random(0xB2D0B3BC)
    for seed in range(cases):
        target=MODE if seed%2==0 else OFF;mode=rng.getrandbits(32)
        lock=rng.choice([f.MAGIC,f.MAGIC,f.MAGIC+1,0,0xFFFFFFFF])
        yield case('random',seed,mode,lock,target,dma1=rng.getrandbits(32),dma2=rng.getrandbits(32),bias=rng.randrange(256))


def initial(cfg):
    images=list(map(bytearray,f.initial(cfg)))
    struct.pack_into('<I',images[2],0xC4,cfg['dma1']);struct.pack_into('<I',images[2],0xD0,cfg['dma2'])
    images[2][0x89]=cfg['bias']
    return list(map(bytes,images))


class Oracle(f.Oracle):
    def __init__(self,cfg,images):
        super().__init__(cfg,images);self.bios_calls=[]
    def off(self):
        sound=self.read(f.GLOBAL,4);lock=self.read(sound,4)
        if((lock-f.MAGIC)&f.MASK)>1:return
        self.write(sound,lock+10,4)
        for dma in [f.IO+0xC4,f.IO+0xD0]:
            if self.read(dma,4)&0x02000000:self.write(dma,0x84400004,4)
        self.write(f.IO+0xC6,0x400,2);self.write(f.IO+0xD2,0x400,2)
        self.bios_calls.append(dict(destination=sound+0x350,control=0x05000318,value=0))
        for index in range(792):self.write(sound+0x350+4*index,0,4)
    def frequency(self,mode):
        original=self.cfg
        self.cfg=dict(original,target=f.SET,mode=mode)
        try:super().run()
        finally:self.cfg=original
    def run(self):
        target=self.cfg['target']
        if target==OFF:self.off()
        elif target==f.VSYNC:self.vsync()
        else:
            p=self.read(f.GLOBAL,4);lock=self.read(p,4)
            if lock==f.MAGIC:
                self.write(p,lock+1,4);mode=self.cfg['mode']
                reverb=mode&255
                if reverb:self.write(p+5,reverb&127,1)
                channels=(mode>>8)&15
                if channels:
                    self.write(p+6,channels,1)
                    for i in range(12):self.write(p+0x50+64*i,0,1)
                volume=(mode>>12)&15
                if volume:self.write(p+7,volume,1)
                if mode&0xB00000:
                    current=self.read(f.IO+0x89,1)
                    self.write(f.IO+0x89,(current&63)|(((mode>>20)&3)<<6),1)
                frequency=mode&0xF0000
                if frequency:self.off();self.frequency(frequency)
                self.write(p,f.MAGIC,4)
        assert self.clocks==len(self.cfg['clock'])
        return self.data,self.trace


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_sound_mode_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    v.OUT=out;v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();dll=v.build_native()
    f.EXPECTED=EXPECTED
    counts={};coverage=set();digest=hashlib.sha256();executions=polls=io_writes=cycles=bios_calls=0
    for number,cfg in enumerate(variants(args.cases)):
        images=initial(cfg);steps=[cfg]
        if cfg['route']=='stop_resume_reconfigure':
            steps+=[dict(cfg,target=OFF,clock=[]),dict(cfg,target=f.VSYNC,clock=[]),
                    dict(cfg,mode=cfg['second_mode'],clock=f.CLOCKS[(cfg['seed']+1)%3])]
            cycles+=1
        rom_trace=native_trace=expected_trace=None
        try:
            for step in steps:
                step=dict(step,model_cpuset_fill32=True,cpuset_calls=[])
                oracle=Oracle(step,images);wanted,expected_trace=oracle.run()
                original,rom_trace,rom_ptr_reads=f.execute(step,images,None,out,coverage)
                candidate,native_trace,native_ptr_reads=f.execute(step,images,dll,out,coverage)
                assert f.comparable(original)==f.comparable(candidate)==f.comparable(wanted),'RAM/PCM or flat I/O images differ'
                assert rom_trace==native_trace==expected_trace,'ordered data read/write trace differs'
                assert rom_ptr_reads==native_ptr_reads==oracle.global_reads,'sound pointer read count differs'
                assert step['cpuset_calls']==oracle.bios_calls,'CpuSet source, destination or control differs'
                bios_calls+=len(oracle.bios_calls);executions+=1;polls+=len(step['clock'])
                io_writes+=sum(row[0]=='write'and f.IO<=row[1]<f.IO+1024 for row in rom_trace)
                digest.update(f.comparable(original));digest.update(json.dumps(rom_trace).encode())
                original[1]=bytes(original[1][:0x7000])+bytes(images[1][0x7000:0x7800])+bytes(original[1][0x7800:])
                images=original
        except Exception as exc:
            failure=dict(case=cfg,error=repr(exc))
            if rom_trace is not None:failure.update(rom_trace=rom_trace,native_trace=native_trace,expected_trace=expected_trace)
            (out/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',cfg['route'],cfg['seed'],repr(exc),flush=True);return 1
        counts[cfg['route']]=counts.get(cfg['route'],0)+1
        if number%256==0:print('Passed sound mode cases:',number+1,flush=True)
    assert coverage==EXPECTED
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,executions=executions,
        stop_resume_reconfigure_cycles=cycles,observed_vcount_reads=polls,observed_io_writes=io_writes,
        reference_cpuset_calls=bios_calls,pcm_fill_words=792,pcm_fill_bytes=3168,reference_bios_image_used=False,
        reference_cpuset_model='SWI 0x0B, exact control 0x05000318, aligned zero source, 792 word writes',
        all_ram_equal=True,io_images_equal=True,ordered_reads_and_writes_equal=True,independent_model_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        mode_instructions_covered=sum(a<=p<b for p in coverage for a,b in NEW_RANGES[:1]),
        off_instructions_covered=sum(a<=p<b for p in coverage for a,b in NEW_RANGES[1:]),
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        zero_mode_fields_preserved=True,reverb_enable_bit_and_mask_verified=True,twelve_channel_status_bytes_only_verified=True,
        bias_flag_gate_and_low_bits_verified=True,dma_word_conditional_and_halfword_order_verified=True,
        pcm_fill_extent_width_and_canaries_verified=True,off_unsigned_lock_guard_verified=True,
        nested_frequency_chain_verified=True,original_mode_lock_restored_verified=True,sound_pointer_reread_verified=True,
        stop_resume_reconfigure_state_carried=True,original_callee_saved_registers_preserved=True,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        frequency_tool_sha256=sha(ROOT/'tools/verify_sound_frequency.py'),native_dll_sha256=sha(out/'music_player_native.dll'),
        compiler_sha256=sha(v.HOST_GCC),host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),rom_sha1=expected,
        results_sha256=digest.hexdigest(),byte_matching=False,full_game_boot=False,
        hardware_register_side_effects_validated=False,real_time_validated=False,audible_output_validated=False,
        cpu='Unicorn ARM926; flat I/O, scripted VCOUNT and modeled CpuSet, not hardware cycles')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'sound mode cases;',executions,'executions;',bios_calls,'modeled fills;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
