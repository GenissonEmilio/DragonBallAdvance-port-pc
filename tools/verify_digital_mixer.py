"""Compare native routing and 10-bit DAC clipping with original mGBA mixing."""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import itertools
import json
import random
import struct
import subprocess
import build_native_game_audio as build

ROOT = Path(__file__).resolve().parents[1]


class Sample(C.Structure):
    _fields_ = [('left', C.c_int16), ('right', C.c_int16),
                ('dac_clipped', C.c_uint8), ('pcm_clipped', C.c_uint8)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_digital_mixer_validation')
    parser.add_argument('--source', type=Path, default=ROOT / 'port/audio/digital_mixer.c')
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args(argv)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ['report.json', 'failed_case.json']:
        (out / name).unlink(missing_ok=True)
    gcc = build.GCC
    mgba = ROOT / 'tools/local/mgba_reference'
    configured = ROOT / 'build/next/psg_reference/mgba_build'
    definitions = ['BUILD_STATIC', 'ENABLE_DIRECTORIES', 'ENABLE_VFS', 'ENABLE_VFS_FD',
                   'M_CORE_GB', 'M_CORE_GBA', '_GNU_SOURCE', '_FILE_OFFSET_BITS=64']
    includes = [mgba / 'include', configured / 'include', mgba / 'src']
    commands = [
        [str(gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared',
         '-I' + str(ROOT / 'port/include'), str(args.source.resolve()), '-o', str(out / 'mixer.dll')],
        [str(gcc), '-std=c11', '-O2', '-shared', *['-D' + n for n in definitions],
         *['-I' + str(p) for p in includes], str(ROOT / 'tools/digital_mixer_oracle.c'),
         str(configured / 'libmgba.a'), '-o', str(out / 'oracle.dll'),
         '-lws2_32', '-lshlwapi', '-lm', '-lole32', '-luuid'],
    ]
    for number, command in enumerate(commands):
        result = subprocess.run(command, capture_output=True, text=True)
        (out / f'build_{number}.log').write_text(json.dumps(command) + '\n' + result.stdout + result.stderr)
        if result.returncode:
            print(result.stderr)
            return 1
    native = C.CDLL(str(out / 'mixer.dll'))
    native.Dbaa_DigitalMix.argtypes = [C.c_int16, C.c_int16, C.c_int8, C.c_int8,
                                      C.c_uint16, C.c_uint16, C.c_uint, C.POINTER(Sample)]
    native.Dbaa_DigitalMix.restype = C.c_int
    oracle = C.CDLL(str(out / 'oracle.dll'))
    oracle.Ref_MixCreate.restype = C.c_void_p
    oracle.Ref_MixDestroy.argtypes = [C.c_void_p]
    oracle.Ref_MixSample.argtypes = [C.c_void_p, C.POINTER(C.c_uint8), C.c_uint16,
                                    C.c_int8, C.c_int8, C.c_uint16, C.c_uint16,
                                    C.POINTER(C.c_int16)]
    state = oracle.Ref_MixCreate()
    assert state
    rng = random.Random(0xDAC512)
    values = [-128, 0, 127] if args.quick else [-128, -64, -1, 0, 1, 64, 127]
    gains = [64, 192] if args.quick else [0, 64, 192, 256]
    biases = [512] if args.quick else [342, 512, 682]
    cases = clipped = pcm_clipped = original_calls = 0
    digest = hashlib.sha256()
    current = None
    try:
        for routes, ratio, volumes, a, b, bias in itertools.product(
                range(16), range(4), range(4), values, values, biases):
            control = ratio | (volumes << 2)
            for bit, mask in enumerate([0x100, 0x200, 0x1000, 0x2000]):
                if routes & (1 << bit):
                    control |= mask
            channels = [rng.randrange(16) for _ in range(4)]
            low = (rng.randrange(256) << 8) | (rng.randrange(8) << 4) | rng.randrange(8)
            if original_calls % 6 == 0:
                channels = [0] * 4
            elif original_calls % 6 == 1:
                channels, low = [15] * 4, 0xFF77
            amplitudes = (C.c_uint8 * 4)(*channels)
            expected = (C.c_int16 * 4)()
            oracle.Ref_MixSample(state, amplitudes, low, a, b, control, bias, expected)
            original_calls += 1
            # Original mGBA masterVolume256 yields (digital DAC value)*48.
            # These bias values keep that reference inside PCM16. Normalize
            # only its post-DAC gain; all routing/ratio/bias/clipping decisions
            # above are performed by the original GBAAudioSample implementation.
            assert expected[2] % 48 == expected[3] % 48 == 0
            digital = [expected[2] // 48, expected[3] // 48]
            for gain in gains:
                current = dict(control=control, bias=bias, gain=gain, a=a, b=b,
                               channels=channels, low_control=low)
                sample = Sample()
                assert native.Dbaa_DigitalMix(expected[0], expected[1], a, b,
                                               control, bias, gain, C.byref(sample))
                wanted = []
                for value in digital:
                    value *= gain
                    value = value // 4 if value >= 0 else -((-value) // 4)
                    wanted.append(max(-32768, min(32767, value)))
                assert [sample.left, sample.right] == wanted, dict(current,
                    native=[sample.left, sample.right], reference=wanted)
                clipped += bool(sample.dac_clipped)
                pcm_clipped += bool(sample.pcm_clipped)
                digest.update(struct.pack('<hhBB', sample.left, sample.right,
                                          sample.dac_clipped, sample.pcm_clipped))
                cases += 1
        assert clipped and (args.quick or pcm_clipped)
        sample = Sample()
        assert not native.Dbaa_DigitalMix(0, 0, 0, 0, 0, 512, 257, C.byref(sample))
        assert not native.Dbaa_DigitalMix(0, 0, 0, 0, 0, 512, 64, None)
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        report = dict(cases=cases, original_mgba_mix_calls=original_calls,
                      quick=args.quick, pcm16_equal_to_original_digital_mix=True,
                      dac_clipped_cases=clipped, pcm16_clipped_cases=pcm_clipped,
                      native_cpu_execution=False, gba_byte_matching=False,
                      analog_output_bit_exact=False, results_sha256=digest.hexdigest(),
                      source_sha256=sha(args.source), header_sha256=sha(ROOT / 'port/include/digital_mixer.h'),
                      oracle_source_sha256=sha(ROOT / 'tools/digital_mixer_oracle.c'),
                      tool_sha256=sha(__file__), library_sha256=sha(out / 'mixer.dll'),
                      oracle_library_sha256=sha(out / 'oracle.dll'), compiler_sha256=sha(gcc))
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print('PASS digital mixer:', cases, 'cases;', original_calls, 'original mixing calls')
        return 0
    except Exception as error:
        (out / 'failed_case.json').write_text(json.dumps(dict(context=current, error=repr(error)), indent=2) + '\n')
        print('FAIL digital mixer:', repr(error))
        return 1
    finally:
        oracle.Ref_MixDestroy(state)


if __name__ == '__main__':
    raise SystemExit(main())
