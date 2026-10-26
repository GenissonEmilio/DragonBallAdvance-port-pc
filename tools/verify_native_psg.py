"""Compare standalone PSG synthesis against pinned mGBA's full GBA I/O path.

This checks a digital hardware adapter, not ROM machine-code byte matching.
The full mGBA library is linked only into the reference DLL.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def bind(path, prefix):
    dll = C.CDLL(str(path))
    definitions = [
        ('Create', [], C.c_void_p), ('Destroy', [C.c_void_p], None),
        ('Advance', [C.c_void_p, C.c_uint64], C.c_int),
        ('Write', [C.c_void_p, C.c_uint64, C.c_uint32, C.c_uint32, C.c_uint], C.c_int),
        ('Status', [C.c_void_p], C.c_uint8),
        ('Sample', [C.c_void_p, C.POINTER(C.c_int16), C.POINTER(C.c_int16)], None),
    ]
    functions = {}
    for name, arguments, result in definitions:
        function = getattr(dll, prefix + '_Psg' + name)
        function.argtypes, function.restype = arguments, result
        functions[name] = function
    return dll, functions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_psg_validation')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--source', type=Path, default=ROOT / 'port/audio/psg_mgba.c')
    args = parser.parse_args(argv)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ['report.json', 'failed_case.json']:
        (out / name).unlink(missing_ok=True)
    result = subprocess.run([sys.executable, str(ROOT / 'tools/build_native_psg.py'),
                             '--out-dir', str(out), '--source', str(args.source.resolve())], capture_output=True, text=True)
    (out / 'native_build.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        print(result.stdout + result.stderr)
        return 1
    compiler = ROOT / 'tools/local/w64devkit/bin/gcc.exe'
    upstream = ROOT / 'tools/local/mgba_reference'
    configured = ROOT / 'build/next/psg_reference/mgba_build'
    definitions = ['BUILD_STATIC', 'ENABLE_DIRECTORIES', 'ENABLE_VFS', 'ENABLE_VFS_FD',
                   'M_CORE_GB', 'M_CORE_GBA', '_GNU_SOURCE', '_FILE_OFFSET_BITS=64']
    includes = [upstream / 'include', configured / 'include', upstream / 'src']
    command = [str(compiler), '-shared', '-std=c11', '-O2',
               *['-D' + n for n in definitions], *['-I' + str(p) for p in includes],
               str(ROOT / 'tools/psg_oracle.c'), str(configured / 'libmgba.a'),
               '-o', str(out / 'oracle.dll'), '-lws2_32', '-lshlwapi', '-lm', '-lole32', '-luuid']
    result = subprocess.run(command, capture_output=True, text=True)
    (out / 'oracle_build.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
    if result.returncode:
        print(result.stderr)
        return 1
    libraries = [bind(out / 'psg.dll', 'Dbaa'), bind(out / 'oracle.dll', 'Ref')]
    digest = hashlib.sha256()
    samples = writes = 0
    # Each channel separately, mixed routing, GBA wave banks/75% volume, then
    # randomized byte/halfword/word writes and exact frame-sequencer boundaries.
    scenarios = [
        [(0x60, 0x16, 2), (0x62, 0xF380, 2), (0x64, 0xC400, 2)],
        [(0x68, 0xA7C1, 2), (0x6C, 0xC6A0, 2)],
        [(0x70, 0x20, 2), *[(0x90 + 4*i, 0x01234567 ^ (i * 0x11111111), 4) for i in range(4)],
         (0x70, 0xC0, 2), (0x72, 0x8060, 2), (0x74, 0xC700, 2)],
        [(0x78, 0xF700, 2), (0x7C, 0xC025, 2)],
        [(0x62, 0xF380, 2), (0x64, 0xC400, 2), (0x68, 0xB280, 2),
         (0x6C, 0xC600, 2), (0x78, 0x9300, 2), (0x7C, 0xC00B, 2)],
    ]
    mixed = scenarios[4] + scenarios[2]
    scenarios += [[(0x88, bias, 2), *mixed] for bias in [0x4200, 0x8200, 0xC200]]
    rng = random.Random(0xBD0E)
    registers = [0x60, 0x62, 0x64, 0x68, 0x6C, 0x70, 0x72, 0x74,
                 0x78, 0x7C, 0x80, 0x84, 0x88, 0x90, 0x94, 0x98, 0x9C]
    current = None
    try:
        for scenario, initial in enumerate(scenarios):
            states = [functions['Create']() for dll, functions in libraries]
            assert all(states), 'PSG allocation failed'
            cycle = 0
            def apply(address, value, width):
                nonlocal writes
                for state, (dll, functions) in zip(states, libraries):
                    assert functions['Write'](state, cycle, 0x04000000 + address, value, width)
                writes += 1
            for address, value, width in [(0x84, 0x80, 2), (0x80, 0xFF77, 2), *initial]:
                apply(address, value, width)
            count = 2500 if args.quick else 20000
            for index in range(count):
                cycle += [1, 197, 349, 1024, 32768][index % 5]
                current = dict(scenario=scenario, index=index, cycle=cycle)
                if index and index % 113 == 0:
                    register = rng.choice(registers)
                    width = rng.choice([1, 2, 4] if register in [0x60, 0x68, 0x70, 0x78, 0x80, 0x90, 0x94, 0x98, 0x9C] else [1, 2])
                    if width == 1:
                        register += rng.randrange(2)
                    value = rng.getrandbits(8 * width)
                    if register == 0x84:
                        value &= 0x80
                    current['write'] = [register, value, width]
                    apply(register, value, width)
                observed = []
                for state, (dll, functions) in zip(states, libraries):
                    assert functions['Advance'](state, cycle)
                    left, right = C.c_int16(), C.c_int16()
                    functions['Sample'](state, C.byref(left), C.byref(right))
                    observed.append((left.value, right.value, functions['Status'](state)))
                assert observed[0] == observed[1], dict(current, native=observed[0], reference=observed[1])
                digest.update(struct.pack('<hhB', *observed[0]))
                samples += 1
            for state, (dll, functions) in zip(states, libraries):
                functions['Destroy'](state)
            print('Passed PSG scenario', scenario + 1, flush=True)
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        report = dict(scenarios=len(scenarios), stereo_samples=samples, writes=writes,
                      raw_digital_psg_equal=True, nr52_equal=True,
                      soundbias_resolutions_tested=[0, 1, 2, 3],
                      dynamic_soundbias_io_tested=True,
                      cpu_execution=False, native_cpu_core_linked=False,
                      gba_byte_matching=False, analog_output_bit_exact=False,
                      rom_pcm_validation=False, quick=args.quick,
                      result_sha256=digest.hexdigest(), native_library_sha256=sha(out / 'psg.dll'),
                      oracle_library_sha256=sha(out / 'oracle.dll'),
                      adapter_sha256=sha(args.source),
                      oracle_sha256=sha(ROOT / 'tools/psg_oracle.c'), tool_sha256=sha(__file__))
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print('PASS native PSG:', samples, 'digital stereo samples;', writes, 'writes')
        return 0
    except Exception as error:
        (out / 'failed_case.json').write_text(json.dumps(dict(context=current, error=repr(error)), indent=2) + '\n')
        print('FAIL PSG:', repr(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
