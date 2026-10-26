"""Compare native audio services with their original ARM routines in isolation."""
from pathlib import Path
import argparse,hashlib,json,random
import verify_music_player as v

ROOT=Path(__file__).resolve().parents[1]
FILTER_SOURCES=[0,0x3fff,0x4000,0x1ffffff,0x02000000,0x0203ffff,
                0x03000000,0x03007fff,0x08000000,0x08A67460,0x09000000,0xffffffff]

def state(seed):
    ew,iw=map(bytearray,v.fixture(seed))
    rng=random.Random(seed+0xA514)
    p=v.PLAYER-v.E;t=v.TRACKS-v.E
    v.w32(ew,p+0x34,0x68736d53)
    v.w32(ew,p+4,rng.choice([0,7,0x80000000]))
    ew[p+8]=seed%4
    v.w16(ew,p+0x24,[0,1,3][seed%3])
    v.w16(ew,p+0x26,[0,1,2,65535][seed%4])
    v.w16(ew,p+0x28,[0,1,2,3,15,16,17,18,255,256,257,0x8000,0xffff][seed%13])
    ew[t]=[0,0x80,0x81,0x84,0x85,0x8f,0xc0][seed%7]
    ew[t+0x18]=[0,1,2,255][seed%4]
    ew[t+0x12]=ew[t+0x13]=255
    ew[t+0x14]=[0,127,128,255][seed%4]
    ew[t+0x15]=[255,128,127,0][seed%4]
    v.w32(ew,t+0x20,v.CHANNELS)
    for j in range(3):
        c=v.CHANNELS-v.E+j*64
        ew[c]=[0,0x10,0x40,0x80,0xff][(seed+j)%5]
        ew[c+1]=[0,1,4,7][(seed+j)%4]
        v.w32(ew,c+0x2c,v.TRACKS)
        v.w32(ew,c+0x30,v.CHANNELS+(j-1)*64 if j else 0)
        v.w32(ew,c+0x34,v.CHANNELS+(j+1)*64 if j<2 else 0)
    if seed%5==4:v.w32(ew,v.CHANNELS-v.E+0x2c,0)
    return ew,iw

def route(name,address,native_name,arm_args,native_args,size,**extra):
    return dict(name=name,address=address,native_name=native_name,arm_args=arm_args,
                native_args=native_args,cover_end=address+size-2,**extra)

def variants(seed):
    initial=state(seed);dest=v.E+0x24000+(seed%8)*256
    ch=v.CHANNELS+(seed%3)*64
    ew,iw=initial
    ew[dest-v.E-16:dest-v.E+176]=b'\xa5'*192
    args=[v.PLAYER,v.TRACKS]
    for name,address,native,size in [
        ('fine',0x0810A4E4,'Dbaa_MusicEventFine',48),
        ('track_stop',0x0810A98C,'Dbaa_MusicTrackStop',68),
        ('volume_pitch',0x0810B6D8,'Dbaa_MusicTrackVolumePitch',180)]:
        yield initial,route(name,address,native,args,args,size)
    for name,address,native,a,size,result in [
        ('copy_table',0x0810A514,'Dbaa_SoundCopyCommandTable',dest,52,True),
        ('clear64',0x0810A4AC,'Dbaa_AudioClear64',dest,24,True),
        ('unlink',0x0810A4C4,'Dbaa_AudioUnlinkChannel',ch,32,True),
        ('fade',0x0810B610,'Dbaa_MusicFadeOutBody',v.PLAYER,200,False)]:
        extra={'observe_reads':[0x08A67460+4*i for i in range(36)]} if name=='copy_table' else {}
        yield initial,route(name,address,native,[a],[a],size,compare_return=result,**extra)
    for name,address,argument,slot in [
        ('clear_wrapper',0x0810B120,dest,0x1cfc),
        ('unlink_wrapper',0x0810B10C,ch,0x1cf8)]:
        copied=[bytearray(ew),bytearray(iw)]
        if seed%2:v.w32(copied[1],slot,v.NEXT+1)
        yield copied,route(name,address,'Dbaa_AudioCall',[argument],[address,argument,0,0],20)
    src=FILTER_SOURCES[seed%len(FILTER_SOURCES)]
    value=random.Random(seed).getrandbits(32)
    yield initial,route('filter',0x0810A52E,'Dbaa_AudioFilterAddress',
                        [v.PLAYER,0,src,value],[src,value],22,compare_return=True,result_register=3)
    extra=[]
    if not (v.E<=src<v.E+0x40000 or v.I<=src<v.I+0x8000 or 0x08000000<=src<0x09000000):
        extra=[(src,bytes([seed&255]))]
    yield initial,route('read_byte',0x0810A52C,'Dbaa_AudioReadByte',
                        [v.PLAYER,0,src,0],[src],24,compare_return=True,result_register=3,extra_memory=extra,observe_reads=[src])
    real=[bytearray(ew),bytearray(iw)]
    p=v.PLAYER-v.E
    v.w32(real[0],p+4,0);real[0][p+8]=3
    v.w16(real[0],p+0x20,150);v.w16(real[0],p+0x22,0);v.w16(real[0],p+0x24,0)
    v.w32(real[1],v.TABLE-v.I,0x0810A4E5)
    for j in range(3):
        t=v.TRACKS-v.E+j*80;real[0][t]=0x80;real[0][t+1]=0
        cp=v.COMMANDS+j*256;v.w32(real[0],t+0x40,cp);real[0][cp-v.E]=0xb1
    yield real,route('player_real_fine',v.START,'Dbaa_MusicPlayerUpdate',[v.PLAYER],[v.PLAYER],602)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=64,help='seeds per service (12 service paths per seed)')
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_audio_helpers_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args=parser.parse_args(argv)
    if args.cases<12:parser.error('at least 12 seeds are required to exercise address boundaries')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    assert hashlib.sha1(v.ROM).hexdigest()==expected
    v.OUT=args.out_dir.resolve();v.OUT.mkdir(parents=True,exist_ok=True)
    (v.OUT/'report.json').unlink(missing_ok=True)
    (v.OUT/'failed_case.json').unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve()
    v.NATIVE=v.build_native()
    counts={}
    for seed in range(args.cases):
        for initial,config in variants(seed):
            reference=v.execute(initial,routine=config)
            native=v.execute(initial,True,routine=config)
            name=config['name']
            if reference!=native:
                offsets=[i for i,(a,b) in enumerate(zip(reference[0],native[0]))if a!=b]
                fail=dict(seed=seed,route=name,ram_offsets=offsets[:32],rom_trace=reference[1],native_trace=native[1],rom_result=reference[2],native_result=native[2])
                (v.OUT/'failed_case.json').write_text(json.dumps(fail,indent=2)+'\n')
                print('FAIL:',json.dumps(fail),flush=True)
                return 1
            counts[name]=counts.get(name,0)+1
        if seed%16==0:print('Passed seeds:',seed+1,'cases:',sum(counts.values()),flush=True)
    assert len(counts)==12 and not v.FALLBACK_TARGETS & v.NATIVE_AUDIO_TARGETS
    sources=[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]
    report=dict(rom_sha1=expected,cases=sum(counts.values()),seeds_per_route=args.cases,routes=counts,
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},
        native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted((ROOT/'port/include').glob('*.h'))},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),shared_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_player.py').read_bytes()).hexdigest(),
        native_dll_sha256=hashlib.sha256((v.OUT/'music_player_native.dll').read_bytes()).hexdigest(),
        all_ram_equal=True,callback_traces_equal=True,meaningful_return_values_equal=True,byte_matching=False,
        source_reads_observed=True,
        full_game_boot=False,host_pointer_bytes=8,native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),
        arm_fallback_targets=sorted(v.FALLBACK_TARGETS),filter_sources=FILTER_SOURCES,
        original_instruction_addresses=[hex(a)for a in sorted(v.COVERAGE)])
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'isolated native/ARM helper cases;',len(v.NATIVE_AUDIO_TARGETS),'entry addresses resolved in C.')
    return 0

if __name__=='__main__':raise SystemExit(main())
