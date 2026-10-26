"""Validate native note creation against the original ROM, including real player dispatch."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import random
import verify_music_player as v

ROOT = Path(__file__).resolve().parents[1]
START, END = 0x0810AA00, 0x0810ABF6
CGB_BANK, OLD_HEAD = v.E+0x8000, v.E+0x9000
VOICES, KEY_MAP = v.E+0x12000, v.E+0x14000


def state(seed, directed=False):
    rng = random.Random(seed+0xAA00)
    ew, iw = map(bytearray, v.fixture(seed % 1000))

    def put(address, value, width=4):
        data, base = (ew, v.E) if v.E <= address < v.E+len(ew) else (iw, v.I)
        data[address-base:address-base+width] = (value & ((1 << (width*8))-1)).to_bytes(width, 'little')

    def get(address, width=4):
        data, base = (ew, v.E) if v.E <= address < v.E+len(ew) else (iw, v.I)
        return int.from_bytes(data[address-base:address-base+width], 'little')

    track = v.TRACKS
    put(v.PLAYER+0x34, 0x68736d53)
    put(v.PLAYER+4, 0)
    put(v.PLAYER+8, 1, 1)
    put(v.PLAYER+9, rng.choice([0,1,127,128,254,255]), 1)
    put(v.PLAYER+0x20, 150, 2)
    put(v.PLAYER+0x22, 0, 2)
    put(v.PLAYER+0x24, 0, 2)
    put(v.PLAYER+0x38, 0)
    for index in range(-1,9):
        put(track+index*80+0x20, 0)
    put(track, rng.choice([0x80,0x81,0x84,0x85,0x8f]), 1)
    put(track+1, 0, 1)
    put(track+5, rng.randrange(256), 1)
    put(track+6, rng.randrange(256), 1)
    put(track+0x1b, rng.choice([0,1,255]), 1)
    put(track+0x1d, rng.choice([0,1,127,128,254,255]), 1)
    put(track+0x40, v.COMMANDS)
    # Running key/velocity/gate are optional; a high-bit byte terminates parsing.
    parameters = seed % 4
    stream = [rng.randrange(128) for _ in range(parameters)] + [0x81,0xb1]
    ew[v.COMMANDS-v.E:v.COMMANDS-v.E+len(stream)] = bytes(stream)
    parsed_key = stream[0] if parameters else get(track+5,1)
    parent = [0,1,2,3,4,5,6,7,8,0x40,0x80,0xc0][seed % 12]
    put(track+0x24, parent, 1)
    put(track+0x25, 60, 1)
    put(track+0x26, rng.randrange(256), 1)
    put(track+0x27, rng.randrange(256), 1)
    put(track+0x28, v.WAVE)
    put(track+0x2c, rng.getrandbits(32))
    ew[KEY_MAP-v.E:KEY_MAP-v.E+256] = bytes(rng.randrange(256) for _ in range(256))
    if parent & 0xc0:
        put(track+0x28, VOICES)
        put(track+0x2c, KEY_MAP)
    for index in range(256):
        tone = VOICES+12*index
        put(tone, rng.choice([0,0,1,2,3,4,7,8,0x40,0x80,0xc0]), 1)
        put(tone+1, rng.randrange(256), 1)
        put(tone+2, rng.randrange(256), 1)
        put(tone+3, rng.choice([0,1,8,0x10,0x70,0x7f,0x80,0xbf,0xc0,0xff]), 1)
        put(tone+4, v.WAVE)
        put(tone+8, rng.getrandbits(32))
    tone_index = get(KEY_MAP+parsed_key,1) if parent & 0x40 else parsed_key
    tone = VOICES+12*tone_index if parent & 0xc0 else track+0x24
    if parent & 0xc0 and directed:
        put(tone, [0,1,4,0x40][seed % 4], 1)
    put(v.WAVE+4, rng.choice([0,1,0x400000,0x7fffffff,0x80000000,0xffffffff]))
    put(v.SOUND+0x1c, 0 if seed % 19 == 18 else CGB_BANK)
    put(v.SOUND+6, seed % 13, 1)
    put(v.SOUND+0x30, v.FREQUENCY+1 if seed % 23 == 22 else 0x0810B78D)
    put(v.SOUND+0x38, START+1)
    put(v.TABLE, 0x0810A4E5)  # Real end-of-track command for player integration.
    priority = min(255, get(v.PLAYER+9,1)+get(track+0x1d,1))
    channels = [v.SOUND+0x50+64*i for i in range(12)] + [CGB_BANK+64*i for i in range(7)] + [OLD_HEAD]
    lists = {owner:[] for owner in [track-80,track,track+80]}
    for index, channel in enumerate(channels):
        for offset in range(64):
            put(channel+offset, rng.randrange(256), 1)
        status = rng.choice([0,0x10,0x20,1,4,0x40,0x80,0xc7,0xff])
        owner = rng.choice([0,track-80,track,track+80])
        if directed:
            # Explicitly force free, higher/lower-priority, releasing, and equal-owner ties.
            mode = seed // 4 % 8
            status = [0,0x80,0x80,0x80,0x40,0xc0,0x80,0x80][mode]
            owner = [0,track,track+80,track-80,track,track+80,track+80,track-80][mode]
            p = [priority,priority,min(priority+1,255),max(priority-1,0),255,0,priority,priority][mode]
        else:
            p = rng.choice([0,255,priority,max(0,priority-1),min(255,priority+1)])
        put(channel, status, 1)
        put(channel+1, 0 if index<12 else 1+(index-12)%7, 1)
        put(channel+0x13, p, 1)
        put(channel+0x24, v.WAVE)
        put(channel+0x2c, owner)
        put(channel+0x30, 0)
        put(channel+0x34, 0)
        if owner:
            lists[owner].append(channel)
    for owner, members in lists.items():
        put(owner+0x20, members[0] if members else 0)
        for index, channel in enumerate(members):
            put(channel+0x30, members[index-1] if index else 0)
            put(channel+0x34, members[index+1] if index+1<len(members) else 0)
    # Substitute the RAM unlink callback without introducing an invalid self-link.
    if seed % 29 == 28:
        put(track+0x24, 0, 1)
        put(track+0x28, v.WAVE)
        put(v.SOUND+6, 1, 1)
        put(v.SOUND+0x50, 0, 1)
        put(v.SOUND+0x50+0x2c, 0)
        put(track+0x20, OLD_HEAD)
        put(OLD_HEAD+0x30, 0)
        put(OLD_HEAD+0x34, 0)
        put(v.I+0x1cf8, v.NEXT+1)
        tone = track+0x24
    reads = [0x03007ff0, v.SOUND+0x1c, v.SOUND+0x30, v.I+0x1cf8]
    reads += list(range(v.COMMANDS,v.COMMANDS+8))
    reads += [tone,tone+1,tone+2,tone+3,tone+4,tone+8,v.WAVE+4]
    if parent & 0x40:
        reads += [KEY_MAP+parsed_key]
    duration = seed % 49
    return [ew,iw], duration, sorted(set(reads)), parameters, parent


def variants(cases):
    for seed in [*range(128), *range(1000,1000+cases)]:
        initial, duration, reads, parameters, parent = state(seed,seed<128)
        yield seed, 'note', initial, dict(address=START,native_name='Dbaa_AudioCall',
            arm_args=[duration,v.PLAYER,v.TRACKS],native_args=[START|(seed&1),duration,v.PLAYER,v.TRACKS],
            cover_start=START,cover_end=END-2,observe_reads=reads), parameters, parent
    for seed in range(128):
        initial, duration, _, parameters, parent = state(seed+2000)
        initial[0][v.TRACKS-v.E]=0x8f
        initial[0][v.TRACKS-v.E+7]=0xcf+duration
        # The player consumes the opcode before dispatching to the actual note routine.
        length = len(initial[0][v.COMMANDS-v.E:v.COMMANDS-v.E+8])
        data = bytes(initial[0][v.COMMANDS-v.E:v.COMMANDS-v.E+length])
        initial[0][v.COMMANDS-v.E:v.COMMANDS-v.E+length+1] = bytes([0xcf+duration])+data
        yield seed, 'player_note', initial, dict(address=v.START,native_name='Dbaa_MusicPlayerUpdate',
            arm_args=[v.PLAYER],native_args=[v.PLAYER],cover_start=START,cover_end=END-2),parameters,parent
    for seed in range(32):
        initial, _, _, parameters, parent = state(seed)
        initial[0][v.TRACKS-v.E+0x18]=seed % 4
        yield seed, 'clear_modulation', initial, dict(address=0x0810AC40,native_name='Dbaa_AudioCall',
            arm_args=[seed,v.TRACKS],native_args=[0x0810AC41,seed,v.TRACKS,0],
            cover_start=START,cover_end=END-2),parameters,parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=1024,help='random seeds plus 288 directed/integration cases')
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/native_sound_update_track_validation')
    parser.add_argument('--helpers-source',type=Path,default=v.HOST_HELPERS_SOURCE)
    args = parser.parse_args(argv)
    if args.cases < 0:
        parser.error('--cases must be nonnegative')
    expected=json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest()!=expected:
        parser.error('requires the exact configured USA ROM SHA-1')
    v.OUT=args.out_dir.resolve()
    v.OUT.mkdir(parents=True,exist_ok=True)
    for name in ['report.json','failed_case.json']:
        (v.OUT/name).unlink(missing_ok=True)
    v.HOST_HELPERS_SOURCE=args.helpers_source.resolve()
    v.NATIVE=v.build_native()
    counts,parsing,voices={},set(),set()
    result_hash=hashlib.sha256()
    for index,(seed,route,initial,config,parameters,parent) in enumerate(variants(args.cases)):
        try:
            reference=v.execute(initial,routine=config)
            native=v.execute(initial,True,routine=config)
            equal=reference==native
            error=None
        except Exception as exc:
            reference=native=None
            equal=False
            error=repr(exc)
        if not equal:
            failure=dict(index=index,seed=seed,route=route,error=error)
            if reference and native:
                failure.update(ram_offsets=[i for i,(a,b)in enumerate(zip(reference[0],native[0]))if a!=b][:32],
                               rom_trace=reference[1],native_trace=native[1])
            (v.OUT/'failed_case.json').write_text(json.dumps(failure,indent=2)+'\n')
            print('FAIL:',json.dumps(failure),flush=True)
            return 1
        counts[route]=counts.get(route,0)+1
        parsing.add(parameters)
        voices.add(parent)
        result_hash.update(reference[0])
        if index%128==0:
            print('Passed note cases:',index+1,flush=True)
    assert not v.FALLBACK_TARGETS & v.NATIVE_AUDIO_TARGETS
    source_paths=[v.HOST_SOURCE,v.HOST_HELPERS_SOURCE]
    report=dict(cases=sum(counts.values()),routes=counts,random_seeds=args.cases,
        all_ram_equal=True,callback_traces_equal=True,resource_reads_equal=True,
        parser_parameter_counts=sorted(parsing),parent_voice_types=sorted(voices),
        original_instructions_covered=len(v.COVERAGE),original_instruction_addresses=[hex(a)for a in sorted(v.COVERAGE)],
        native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),arm_fallback_targets=sorted(v.FALLBACK_TARGETS),
        native_sources_sha256={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in source_paths},
        native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted((ROOT/'port/include').glob('*.h'))},
        native_dll_sha256=hashlib.sha256((v.OUT/'music_player_native.dll').read_bytes()).hexdigest(),
        compiler_sha256=hashlib.sha256(v.HOST_GCC.read_bytes()).hexdigest(),
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        shared_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_player.py').read_bytes()).hexdigest(),
        rom_sha1=expected,host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),byte_matching=False,full_game_boot=False,
        cpu='Unicorn ARM926; functional reference, not ARM7 timing or GBA hardware',results_sha256=result_hash.hexdigest())
    (v.OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS:',report['cases'],'note/native ARM cases; instructions:',len(v.COVERAGE),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
