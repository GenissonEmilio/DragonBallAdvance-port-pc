"""Compare native PCM/CGB frequency results and data reads with the exact USA ROM.

Pure routines use a persistent ARM reference to permit exhaustive byte inputs.
No reference result is calculated from the native algorithm or tables in Python.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import random
import struct

from unicorn import UC_HOOK_MEM_WRITE
import verify_music_player as v

ROOT = Path(__file__).resolve().parents[1]
PCM, CGB = 0x0810AC90, 0x0810B78C
FINES = [0, 1, 127, 128, 254, 255]
KEYS = [0, 20, 21, 35, 36, 79, 80, 81, 165, 166, 167, 255]
WAVE_FREQUENCIES = [0, 1, 255, 256, 0xffff, 0x10000, 0x400000,
                    0x7fffffff, 0x80000000, 0xffffff00, 0xfffffffe, 0xffffffff]


def vectors(exhaustive):
    # Every note, six interpolation boundaries and twelve unsigned products.
    for frequency in WAVE_FREQUENCIES:
        for key in range(256):
            for fine in FINES:
                yield 'pcm_limits', PCM, v.WAVE, key, fine, frequency
    # All channel byte values, with noise/tone and lower/upper note boundaries.
    for channel in range(256):
        for key in KEYS:
            for fine in FINES:
                yield 'cgb_channels', CGB, channel, key, fine, 0
    if exhaustive:
        for key in range(256):
            for fine in range(256):
                yield 'pcm_exhaustive', PCM, v.WAVE, key, fine, 0x400000
                yield 'cgb_tone_exhaustive', CGB, 1, key, fine, 0
                yield 'cgb_noise_exhaustive', CGB, 4, key, fine, 0
    rng = random.Random(0xAC90B78C)
    # The public dispatcher takes uint32_t; GBA u8 arguments discard upper bits.
    for _ in range(2048):
        key, fine, frequency, channel = [rng.getrandbits(32) for _ in range(4)]
        yield 'pcm_wide_arguments', PCM, v.WAVE, key, fine, frequency
        yield 'cgb_wide_arguments', CGB, channel, key, fine, 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='omit only the three exhaustive key/fine sweeps')
    parser.add_argument('--out-dir', type=Path, default=ROOT/'build/native_audio_frequency_validation')
    parser.add_argument('--helpers-source', type=Path, default=v.HOST_HELPERS_SOURCE)
    args = parser.parse_args(argv)
    expected = json.loads((ROOT/'config/matching.json').read_text())['rom_sha1']
    if hashlib.sha1(v.ROM).hexdigest() != expected:
        parser.error('requires the exact configured USA ROM SHA-1')
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out/'report.json').unlink(missing_ok=True)
    (out/'failed_case.json').unlink(missing_ok=True)
    v.OUT = out
    v.HOST_HELPERS_SOURCE = args.helpers_source.resolve()
    dll = v.build_native()
    fn = dll.Dbaa_AudioCall
    fn.argtypes = [ctypes.POINTER(v.Host), *[ctypes.c_uint32]*4]
    fn.restype = ctypes.c_uint32
    uc = v.Uc(v.UC_ARCH_ARM, v.UC_MODE_THUMB)
    uc.ctl_set_cpu_model(v.UC_CPU_ARM_926)
    uc.mem_map(0x08000000, 0x1000000)
    uc.mem_write(0x08000000, v.ROM)
    uc.mem_map(v.E, 0x40000)
    uc.mem_map(v.I, 0x8000)
    # Only the wave header's frequency word is read from RAM.
    stack = v.I + 0x7800
    errors, original_reads, native_reads = [], [], []
    coverage = set()
    observing_coverage = True

    def resource(address):
        return (0x08A674F0 <= address < 0x08A675D4 or
                0x08A675EC <= address < 0x08A676C4 or address == v.WAVE+4)

    def read(user, address, width):
        try:
            value = int.from_bytes(uc.mem_read(address, width), 'little')
            native_reads.append((address, width, value))
            return value
        except Exception as exc:
            errors.append(str(exc))
            return 0

    def write(user, address, value, width):
        errors.append(('native write in pure frequency routine', address, width, value))

    def call(user, target, a0, a1, a2):
        errors.append(('unexpected ARM fallback', target, a0, a1, a2))
        return 0

    def observe_read(machine, access, address, width, value, data):
        if resource(address):
            original_reads.append((address, width, int.from_bytes(machine.mem_read(address, width), 'little')))

    def observe_write(machine, access, address, width, value, data):
        if not (stack-128 <= address and address+width <= stack):
            errors.append(('original write outside dead stack', address, width, value))

    def observe_code(machine, address, size, data):
        coverage.add(address)

    uc.hook_add(v.UC_HOOK_MEM_READ, observe_read)
    uc.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    code_hook = uc.hook_add(v.UC_HOOK_CODE, observe_code)
    host = v.Host(None, v.READ(read), v.WRITE(write), v.CALL(call))
    saved = [0xC0DE0000+i for i in range(8)]
    counts, maximum = {}, 0
    result_hash = hashlib.sha256()
    for index, (route, target, a0, key, fine, frequency) in enumerate(vectors(not args.quick)):
        original_reads.clear()
        native_reads.clear()
        uc.mem_write(v.WAVE+4, struct.pack('<I', frequency))
        # Reset full call state, including the interworking CPU state after UMULL.
        uc.reg_write(v.UC_ARM_REG_CPSR, 0x1f | 0x20)
        for reg, value in zip(v.REGS[:4], [a0, key, fine, 0]):
            uc.reg_write(reg, value)
        for reg, value in zip(v.REGS[4:], saved):
            uc.reg_write(reg, value)
        uc.reg_write(v.UC_ARM_REG_SP, stack)
        uc.reg_write(v.UC_ARM_REG_LR, v.STOP+1)
        uc.emu_start(target | 1, v.STOP, count=256)
        assert uc.reg_read(v.UC_ARM_REG_PC) == v.STOP, 'ARM instruction limit'
        assert uc.reg_read(v.UC_ARM_REG_SP) == stack
        assert [uc.reg_read(r) for r in v.REGS[4:]] == saved
        reference = uc.reg_read(v.UC_ARM_REG_R0)
        candidate = fn(ctypes.byref(host), target | (index & 1), a0, key, fine)
        if errors or reference != candidate or original_reads != native_reads:
            failure = dict(index=index, route=route, target=hex(target), a0=a0, key=key, fine=fine,
                           wave_frequency=frequency, rom_result=reference, native_result=candidate,
                           rom_reads=original_reads, native_reads=native_reads, errors=errors)
            (out/'failed_case.json').write_text(json.dumps(failure, indent=2)+'\n')
            print('FAIL:', json.dumps(failure), flush=True)
            return 1
        counts[route] = counts.get(route, 0)+1
        maximum = max(maximum, reference)
        result_hash.update(struct.pack('<7I', target, a0, key, fine, frequency, reference, candidate))
        # First 36,864 cases cover all clamps, table branches and both CPU modes.
        if observing_coverage and index == 36863:
            uc.hook_del(code_hook)
            observing_coverage = False
        if index % 20000 == 0:
            print('Passed frequency cases:', index+1, flush=True)
    sources = [v.HOST_SOURCE, v.HOST_HELPERS_SOURCE]
    report = dict(cases=sum(counts.values()), routes=counts, exhaustive_key_fine=not args.quick,
                  rom_sha1=expected, all_results_equal=True, source_reads_equal=True,
                  game_ram_unchanged=True, callee_saved_registers_preserved=True,
                  arm_fallback_targets=[], native_frequency_targets=[PCM, CGB],
                  native_audio_targets=sorted(v.NATIVE_AUDIO_TARGETS),
                  byte_matching=False, full_game_boot=False, host_pointer_bytes=ctypes.sizeof(ctypes.c_void_p),
                  cpu='Unicorn ARM926; functional comparison, not ARM7 timing or GBA devices',
                  native_sources_sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  native_headers_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'port/include').glob('*.h'))},
                  native_dll_sha256=hashlib.sha256((out/'music_player_native.dll').read_bytes()).hexdigest(),
                  compiler_sha256=hashlib.sha256(v.HOST_GCC.read_bytes()).hexdigest(),
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  shared_tool_sha256=hashlib.sha256((ROOT/'tools/verify_music_player.py').read_bytes()).hexdigest(),
                  original_instruction_addresses=[hex(a) for a in sorted(coverage)],
                  results_sha256=result_hash.hexdigest(), maximum_result=maximum,
                  wave_frequencies=WAVE_FREQUENCIES, fines=FINES, channel_bytes_tested=256,
                  key_bytes_tested=256, fine_bytes_tested=256 if not args.quick else len(FINES))
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS:', report['cases'], 'native/ROM frequency cases; identical results and resource reads.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
