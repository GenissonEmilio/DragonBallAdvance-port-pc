"""Compare native sound setup with ROM, including modeled BIOS zero fills.

Observe all game RAM, command-template reads, ordered MMIO and lifecycle state.
Callbacks are installed as GBA address keys; CGB update/stop are not executed.
"""
from pathlib import Path
import argparse,ctypes,hashlib,json,random,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
import verify_sound_frequency as f
import verify_sound_mode as m
import verify_music_player as v

ROOT=Path(__file__).resolve().parents[1]
INIT,EXTEND,DUMMY=0x0810B134,0x0810AFF0,0x0810C224
SOUND,CHANNELS,COMMANDS,TEMPLATE=0x03000CC0,0x03001D00,0x03001C70,0x08A67460
NEW_RANGES=[(INIT,0x0810B1EC),(EXTEND,0x0810B0B8),(DUMMY,DUMMY+2)]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
NEW={i.address for a,b in NEW_RANGES for i in MD.disasm(v.ROM[a-0x08000000:b-0x08000000],a)}
COPY={i.address for i in MD.disasm(v.ROM[0x10A514:0x10A52A],0x0810A514)}
FILTER={0x0810A52E,0x0810A530,0x0810A532,0x0810A540,0x0810A542}
EXPECTED=NEW|m.EXPECTED|COPY|FILTER
PATCHES=[(8,0x0810BFAD),(17,0x0810AC69),(19,0x0810AC7D),(28,0x0810C105),(29,0x0810AC01),
         (30,0x0810B22D),(31,0x0810A98D),(32,0x0810B611),(33,0x0810B6D9)]
BASE_WATCH=f.watched
def watched(address,width):return BASE_WATCH(address,width)or TEMPLATE<=address<TEMPLATE+144


def case(route,seed,target=INIT,sound=SOUND,channels=CHANNELS,lock=f.MAGIC,**extra):
    cfg=dict(route=route,seed=seed,target=target,sound=sound,channels=channels,lock=lock,
             dma1=0xA5120037,dma2=0x5B34007D,bias=255)
    cfg.update(extra);cfg['mode']=sound if target==INIT else channels if target==EXTEND else 0xCAFEBABE
    cfg['clock']=f.CLOCKS[seed%3]if target==INIT else[]
    return cfg


def variants(cases):
    for seed,cfg in enumerate([{},dict(sound=v.E+0x2000,channels=v.E+0x5000,lock=0),
        dict(target=EXTEND),dict(target=EXTEND,lock=0),dict(target=EXTEND,lock=f.MAGIC+1),dict(target=DUMMY)]):
        yield case('guards',seed,**cfg)
    for first in m.DMA_WORDS:
        for second in m.DMA_WORDS:yield case('init_dma_words',first^second,dma1=first,dma2=second)
    for bias in range(256):yield case('init_bias_bytes',bias,bias=bias)
    for lock in m.LOCKS:yield case('init_old_locks',lock,lock=lock)
    for sound in [SOUND,v.E+0x2000,v.E+0x10000,v.I+0x2000,v.I+0x4000,v.I+0x1C40]:
        for flags in range(4):
            yield case('init_placements',sound+flags,sound=sound,dma1=(flags&1)<<25,dma2=((flags>>1)&1)<<25)
    for lock in m.LOCKS:yield case('extend_locks',lock,target=EXTEND,lock=lock)
    for channels in [CHANNELS,v.E+0x6000,v.E+0x10000,v.I+0x3000,v.I+0x6000,v.E+0x30000]:
        for lock in [f.MAGIC,0]:yield case('extend_placements',channels+lock,target=EXTEND,channels=channels,lock=lock)
    for channels in [v.E+0x2000+off for off in [0,4,0x1C,0x28,0x34,0x50,0x350]]+[COMMANDS+off for off in [0,0x20,0x84]]:
        yield case('extend_aliases',channels,target=EXTEND,sound=v.E+0x2000,channels=channels)
    for seed in range(16):yield case('extend_table_sentinels',seed,target=EXTEND,table_seed=seed)
    for seed in range(64):yield case('extend_io_images',seed,target=EXTEND,lock=f.MAGIC if seed&1 else 0)
    for seed in range(32):
        yield case('lifecycle',seed,sound=SOUND if seed&1 else v.E+0x2000,
                   channels=CHANNELS if seed&1 else v.E+0x5000)
    for sound in [SOUND,v.E+0x2000]:
        for lock in [f.MAGIC,f.MAGIC+10,0,0xFFFFFFFF]:
            yield case('pointer_rebound',sound+lock,sound=sound,rebound=v.I+0x3000,rebound_lock=lock)
    rng=random.Random(0xB134AFF0)
    for seed in range(cases):
        target=INIT if seed%2==0 else EXTEND
        sound=rng.choice([SOUND,v.E+0x2000,v.E+0x10000,v.I+0x2000])
        channels=rng.choice([CHANNELS,v.E+0x5000,v.I+0x6000])
        yield case('random',seed,target,sound,channels,rng.choice([f.MAGIC,f.MAGIC,0,f.MAGIC+1,0xFFFFFFFF]),
                   dma1=rng.getrandbits(32),dma2=rng.getrandbits(32),bias=rng.randrange(256),table_seed=seed)


def initial(cfg):
    images=list(map(bytearray,m.initial(cfg)))
    # Initialization must replace an unrelated previous global pointer.
    if cfg['target']==INIT:struct.pack_into('<I',images[1],f.GLOBAL-v.I,v.E+0x18000)
    if 'table_seed'in cfg:
        rng=random.Random(cfg['table_seed'])
        for index in range(36):struct.pack_into('<I',images[1],COMMANDS-v.I+4*index,rng.getrandbits(32))
    return list(map(bytes,images))


class Oracle(m.Oracle):
    def fill(self,destination,control):
        self.bios_calls.append(dict(destination=destination,control=control,value=0))
        for index in range(control&0x1FFFFF):self.write(destination+4*index,0,4)
    def initialize(self):
        p=self.cfg['mode'];self.write(p,0,4)
        for dma in [f.IO+0xC4,f.IO+0xD0]:
            if self.read(dma,4)&0x02000000:self.write(dma,0x84400004,4)
        self.write(f.IO+0xC6,0x400,2);self.write(f.IO+0xD2,0x400,2)
        self.write(f.IO+0x84,0x8F,2);self.write(f.IO+0x82,0xA90E,2)
        bias=self.read(f.IO+0x89,1);self.write(f.IO+0x89,(bias&63)|64,1)
        for address,value in [(f.IO+0xBC,p+0x350),(f.IO+0xC0,f.IO+0xA0),
                              (f.IO+0xC8,p+0x980),(f.IO+0xCC,f.IO+0xA4),(f.GLOBAL,p)]:
            self.write(address,value,4)
        self.fill(p,0x050003EC)
        self.write(p+6,8,1);self.write(p+7,15,1)
        for offset,target in [(0x38,0x0810AA01),(0x28,DUMMY+1),(0x2C,DUMMY+1),(0x30,DUMMY+1),(0x3C,DUMMY+1)]:
            self.write(p+offset,target,4)
        for index in range(36):self.write(COMMANDS+4*index,self.read(TEMPLATE+4*index,4),4)
        self.write(p+0x34,COMMANDS,4);self.frequency(0x40000);self.write(p,f.MAGIC,4)
    def extend(self):
        for address,width,value in [(0x84,2,0x8F),(0x80,2,0),(0x63,1,8),(0x69,1,8),(0x79,1,8),
            (0x65,1,0x80),(0x6D,1,0x80),(0x7D,1,0x80),(0x70,1,0),(0x80,1,0x77)]:
            self.write(f.IO+address,value,width)
        p=self.read(f.GLOBAL,4);lock=self.read(p,4)
        if lock!=f.MAGIC:return
        self.write(p,lock+1,4)
        for slot,target in PATCHES:self.write(COMMANDS+slot*4,target,4)
        channels=self.cfg['mode']
        for offset,value in [(0x1C,channels),(0x28,0x0810B8ED),(0x2C,0x0810B835),(0x30,0x0810B78D)]:
            self.write(p+offset,value,4)
        self.write(p+12,0,1);self.fill(channels,0x05000040)
        for offset,value in [(1,1),(0x1C,0x11),(0x41,2),(0x5C,0x22),(0x81,3),(0x9C,0x44),(0xC1,4),(0xDC,0x88)]:
            self.write(channels+offset,value,1)
        self.write(p,lock,4)
    def run(self):
        if self.cfg['target']==INIT:self.initialize()
        elif self.cfg['target']==EXTEND:self.extend()
        elif self.cfg['target']!=DUMMY:return super().run()
        assert self.clocks==len(self.cfg['clock'])
        return self.data,self.trace


def image_word(images,address):
    return struct.unpack_from('<I',images[0]if address<v.I else images[1],address-(v.E if address<v.I else v.I))[0]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=512)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_sound_initialization_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<0:parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:parser.error('requires exact configured USA ROM')
    out=args.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:(out/name).unlink(missing_ok=True)
    v.OUT=out;v.HOST_HELPERS_SOURCE=args.helpers_source.resolve();dll=v.build_native()
    f.EXPECTED=EXPECTED;f.watched=watched
    counts={};coverage=set();digest=hashlib.sha256();executions=polls=io_writes=lifecycle=bios_calls=dummy_calls=0
    bios_controls={};metadata_checks=0
    for number,cfg in enumerate(variants(args.cases)):
        images=initial(cfg);steps=[cfg]
        if cfg['route']=='lifecycle':
            steps +=[dict(cfg,target=DUMMY,mode=0xAABBCCDD,clock=[],dummy_offset=offset)for offset in [0x28,0x2C,0x30,0x3C]]
            steps +=[dict(cfg,target=EXTEND,mode=cfg['channels'],clock=[]),
                     dict(cfg,target=m.MODE,mode=(((cfg['seed']%15)+1)<<16)|0x00A03580,clock=f.CLOCKS[cfg['seed']%3]),
                     dict(cfg,target=m.OFF,mode=0,clock=[]),dict(cfg,target=f.VSYNC,mode=0,clock=[]),
                     dict(cfg,target=INIT,mode=cfg['sound'],clock=f.CLOCKS[(cfg['seed']+1)%3]),
                     dict(cfg,target=EXTEND,mode=cfg['channels'],clock=[])]
            lifecycle+=1
        rom_trace=native_trace=expected_trace=None
        try:
            for step in steps:
                step=dict(step,model_cpuset_fill32=True,cpuset_calls=[])
                if 'dummy_offset'in step:
                    pointer=image_word(images,cfg['sound']+step['dummy_offset'])
                    assert pointer==DUMMY+1;step['target']=pointer&~1;dummy_calls+=1
                oracle=Oracle(step,images);wanted,expected_trace=oracle.run()
                original,rom_trace,rom_ptr_reads=f.execute(step,images,None,out,coverage)
                candidate,native_trace,native_ptr_reads=f.execute(step,images,dll,out,coverage)
                assert f.comparable(original)==f.comparable(candidate)==f.comparable(wanted),'RAM, setup tables or I/O images differ'
                assert rom_trace==native_trace==expected_trace,'ordered read/write trace differs'
                assert rom_ptr_reads==native_ptr_reads==oracle.global_reads
                assert step['cpuset_calls']==oracle.bios_calls,'CpuSet parameters differ'
                for call in oracle.bios_calls:
                    key=hex(call['control']);bios_controls[key]=bios_controls.get(key,0)+1
                bios_calls+=len(oracle.bios_calls);executions+=1;polls+=len(step['clock'])
                io_writes+=sum(row[0]=='write'and f.IO<=row[1]<f.IO+1024 for row in rom_trace)
                if cfg['route']=='lifecycle'and step['target']==EXTEND:
                    p=cfg['sound'];channels=cfg['channels']
                    assert image_word(original,p)==f.MAGIC and image_word(original,p+0x1C)==channels
                    assert [image_word(original,p+off)for off in [0x28,0x2C,0x30]]==[0x0810B8ED,0x0810B835,0x0810B78D]
                    table=list(struct.unpack_from('<36I',v.ROM,TEMPLATE-0x08000000))
                    for slot,pointer in PATCHES:table[slot]=pointer
                    assert [image_word(original,COMMANDS+i*4)for i in range(36)]==table
                    assert all((x&~1)in v.NATIVE_AUDIO_TARGETS for x in table)
                    metadata_checks+=1
                digest.update(f.comparable(original));digest.update(json.dumps(rom_trace).encode())
                original[1]=bytes(original[1][:0x7000])+bytes(images[1][0x7000:0x7800])+bytes(original[1][0x7800:])
                images=original
        except Exception as exc:
            failure=dict(case=cfg,error=repr(exc))
            if rom_trace is not None:failure.update(rom_trace=rom_trace,native_trace=native_trace,expected_trace=expected_trace)
            (out/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',cfg['route'],cfg['seed'],repr(exc),flush=True);return 1
        counts[cfg['route']]=counts.get(cfg['route'],0)+1
        if number%128==0:print('Passed sound initialization cases:',number+1,flush=True)
    assert coverage==EXPECTED
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    report=dict(cases=sum(counts.values()),routes=counts,random_cases=args.cases,executions=executions,
        lifecycle_sequences=lifecycle,lifecycle_metadata_checks=metadata_checks,installed_dummy_callback_calls=dummy_calls,
        observed_vcount_reads=polls,observed_io_writes=io_writes,reference_cpuset_calls=bios_calls,reference_cpuset_controls=bios_controls,
        soundinfo_zero_fill_bytes=4016,cgb_zero_fill_bytes=256,reference_bios_image_used=False,
        all_ram_equal=True,io_images_equal=True,ordered_reads_and_writes_equal=True,independent_model_equal=True,
        original_instructions_covered=len(coverage),original_instruction_addresses=[hex(a)for a in sorted(coverage)],
        initialize_instructions_covered=sum(NEW_RANGES[0][0]<=p<NEW_RANGES[0][1]for p in coverage),
        extend_instructions_covered=sum(NEW_RANGES[1][0]<=p<NEW_RANGES[1][1]for p in coverage),
        dummy_instructions_covered=int(DUMMY in coverage),full_zero_fill_extent_and_canaries_verified=True,
        fifo_dma_sources_and_widths_verified=True,initialize_overrides_old_pointer_and_lock_verified=True,
        template_copy_and_nine_patches_verified=True,extend_hardware_before_lock_guard_verified=True,
        cgb_fields_and_alias_order_verified=True,global_pointer_reread_and_cached_argument_verified=True,
        initialized_table_bound_slots=36,lifecycle_state_carried=True,
        installed_cgb_callbacks=[0x0810B834,0x0810B8EC],installed_cgb_callbacks_pending_native=[],pending_cgb_callbacks_executed=False,
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=[],native_new_services_fallback_to_arm=False,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha(p)for p in[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]},
        native_headers_sha256={str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=sha(__file__),shared_tool_sha256=sha(ROOT/'tools/verify_music_player.py'),
        frequency_tool_sha256=sha(ROOT/'tools/verify_sound_frequency.py'),mode_tool_sha256=sha(ROOT/'tools/verify_sound_mode.py'),
        native_dll_sha256=sha(out/'music_player_native.dll'),compiler_sha256=sha(v.HOST_GCC),
        host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),rom_sha1=expected,results_sha256=digest.hexdigest(),
        byte_matching=False,full_game_boot=False,hardware_register_side_effects_validated=False,real_time_validated=False,
        audible_output_validated=False,cpu='Unicorn ARM926; flat I/O, scripted VCOUNT and modeled CpuSet, not hardware cycles')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'sound initialization cases;',executions,'executions;',bios_calls,'modeled fills;',len(coverage),'instructions',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
