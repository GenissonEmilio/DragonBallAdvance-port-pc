"""Compare chip output across the 32-bit hardware cycle-counter rollover."""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import struct
from verify_native_psg import bind

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_psg_wrap_validation')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').unlink(missing_ok=True)
    source = ROOT / 'build/native_psg_bias_validation'
    proof = json.loads((source / 'build.json').read_text())
    report = json.loads((source / 'report.json').read_text())
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for field in ['sources_sha256', 'headers_sha256', 'objects_sha256']:
        assert all(sha(ROOT / p) == h for p, h in proof[field].items())
    assert sha(source / 'psg.dll') == report['native_library_sha256']
    assert sha(source / 'oracle.dll') == report['oracle_library_sha256']
    libraries = [bind(source / 'psg.dll', 'Dbaa'), bind(source / 'oracle.dll', 'Ref')]
    digest = hashlib.sha256()
    snapshots = writes = nonzero = 0
    current = None
    states = []
    try:
        for resolution in range(4):
            states = [functions['Create']() for dll, functions in libraries]
            assert all(states)
            cycle = (1 << 32) - 65536
            for state, (dll, functions) in zip(states, libraries):
                assert functions['Advance'](state, cycle)
            def apply(address, value, width=2):
                nonlocal writes
                for state, (dll, functions) in zip(states, libraries):
                    assert functions['Write'](state, cycle, 0x04000000 + address, value, width)
                writes += 1
            for address, value in [(0x84, 0x80), (0x80, 0xFF77), (0x88, 512 | (resolution << 14)),
                                   (0x62, 0xF380), (0x64, 0x8400), (0x68, 0xB280),
                                   (0x6C, 0x8600), (0x78, 0x9300), (0x7C, 0x800B), (0x70, 0x20)]:
                apply(address, value)
            for i in range(4):
                apply(0x90 + 4*i, 0x01234567 ^ (i * 0x11111111), 4)
            for address, value in [(0x70, 0xC0), (0x72, 0x8060), (0x74, 0x8700)]:
                apply(address, value)
            timestamps = sorted({cycle + i*197 for i in range(1000)} |
                                {(1 << 32) + i for i in [-32769, -32768, -1025, -1024, -1, 0, 1, 1023, 1024, 32767, 32768]})
            for index, cycle in enumerate(timestamps):
                current = dict(resolution=resolution, index=index, cycle=cycle)
                if index and index % 113 == 0:
                    apply(0x7C, 0x8000 | ((index // 113) & 15))
                observed = []
                for state, (dll, functions) in zip(states, libraries):
                    assert functions['Advance'](state, cycle)
                    left, right = C.c_int16(), C.c_int16()
                    functions['Sample'](state, C.byref(left), C.byref(right))
                    observed.append((left.value, right.value, functions['Status'](state)))
                assert observed[0] == observed[1], dict(current, native=observed[0], reference=observed[1])
                digest.update(struct.pack('<QhhB', cycle, *observed[0]))
                nonzero += bool(observed[0][0] or observed[0][1])
                snapshots += 1
            for state, (dll, functions) in zip(states, libraries):
                functions['Destroy'](state)
            states = []
            print('Passed PSG rollover resolution', resolution, flush=True)
        assert nonzero
        result = dict(stereo_snapshots=snapshots, writes=writes, nonzero_snapshots=nonzero,
                      soundbias_resolutions=[0, 1, 2, 3], counter_rollover=1 << 32,
                      raw_digital_psg_equal=True, nr52_equal=True, cpu_execution=False,
                      gba_byte_matching=False, analog_output_bit_exact=False,
                      results_sha256=digest.hexdigest(), tool_sha256=sha(__file__),
                      chip_report_sha256=sha(source / 'report.json'), chip_build_sha256=sha(source / 'build.json'))
        (out / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
        print('PASS PSG cycle rollover:', snapshots, 'snapshots')
        return 0
    except Exception as error:
        (out / 'failed_case.json').write_text(json.dumps(dict(context=current, error=repr(error)), indent=2) + '\n')
        print('FAIL PSG rollover:', repr(error))
        return 1
    finally:
        for state, (dll, functions) in zip(states, libraries):
            functions['Destroy'](state)


if __name__ == '__main__':
    raise SystemExit(main())
