"""Replay ROM-validated PCM8 buffers through the actual game audio consumer.

The immutable original-song corpus already compares every producer buffer with
the ROM. Re-execute its frozen native producer, verify its raw-buffer digest and
legacy PCM against that corpus, then compare the new game's independent
timestamp consumer byte for byte. This test executes no ARM/Thumb CPU.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import os
import struct
import build_native_game_audio as build
import verify_windows_audio as windows
import verify_song_playback as songs

ROOT = Path(__file__).resolve().parents[1]


def bind(path):
    dll = C.CDLL(str(path))
    functions = {}
    signatures = {
        'Init': ([C.c_int], C.c_int), 'Advance': ([C.c_uint32], C.c_int),
        'Write': ([C.c_uint32, C.c_uint32, C.c_uint], C.c_int),
        'VBlank': ([], None), 'Close': ([], None), 'Error': ([], C.c_char_p),
        'ProbeMemory': ([C.c_uint32, C.c_void_p, C.c_size_t, C.c_int], C.c_int),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(dll, 'Dbaa_GameAudio' + name)
        function.argtypes, function.restype = arguments, result
        functions[name] = function
    return dll, functions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_game_audio_validation')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args(argv)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ['report.json', 'failed_case.json']:
        (out / name).unlink(missing_ok=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    reference = ROOT / 'build/native_song_validation'
    ref = json.loads((reference / 'report.json').read_text())
    assert not ref['quick'] and ref['original_song_frames'] == 1800
    assert ref['pcm8_bytes_equal'] and ref['pcm16_timestamp_oracle_equal']
    assert ref['cgb_active_frames'] == 0
    assert ref['rom_sha1'] == hashlib.sha1((ROOT / 'baserom.gba').read_bytes()).hexdigest()
    assert all(sha(ROOT / p) == h for p, h in ref['native_build']['sources_sha256'].items())
    assert ref['native_build']['dll_sha256'] == sha(reference / 'audio_runtime.dll')
    expected = (reference / 'song_reference.pcm').read_bytes()
    assert hashlib.sha256(expected).hexdigest() == ref['pcm16_sha256']
    consumer_dll = build.build(out, args.source)
    library, consumer = bind(consumer_dll)
    producer_library = C.CDLL(str(reference / 'audio_runtime.dll'))
    producer = windows.Runtime(producer_library)
    songs.bind(producer)
    frame = -1
    try:
        producer.reset()
        producer.Observe(producer.r, windows.OBS(), None)
        producer.Gain(producer.r, 64)
        # Python uses UCRT, while this MinGW DLL uses MSVCRT. Synchronize the
        # latter's cached environment too; child executables get these paths at
        # process startup and do not need this test-only CRT bridge.
        crt = C.CDLL('msvcrt.dll')
        crt._putenv_s.argtypes = [C.c_char_p, C.c_char_p]
        crt._putenv_s.restype = C.c_int
        for name, path in [('DBAA_GAME_PCM', out / 'game.pcm'),
                           ('DBAA_GAME_AUDIO_REPORT', out / 'consumer_report.json')]:
            os.environ[name] = str(path)
            assert crt._putenv_s(name.encode(), str(path).encode()) == 0
        assert consumer['Init'](0), consumer['Error']()
        def memory(address, data):
            buffer = C.create_string_buffer(data)
            assert consumer['ProbeMemory'](address, buffer, len(data), 1)
        # No PSG voice is active in this corpus. Enable its master circuit as
        # the game does, so hardware status and copied I/O agree during replay.
        assert consumer['Write'](0x84, 0x80, 1)
        raw = hashlib.sha256()
        legacy_pcm = bytearray()
        frames = 80 if args.quick else ref['original_song_frames']
        offsets = set()
        for frame in range(frames):
            action = ref['actions'].get(str(frame))
            if action:
                name, value = action
                if name == 'start':
                    assert producer.StartSong(producer.r, value)
                elif name == 'player_stop':
                    assert producer.StopPlayer(producer.r, value)
                elif name == 'global_stop':
                    assert producer.StopAll(producer.r)
                else:
                    raise AssertionError(action)
            assert producer.Frame(producer.r), producer.Error(producer.r)
            sound_pointer = producer.memory(0x03007FF0, size=4)
            sound = struct.unpack('<I', sound_pointer)[0]
            memory(0x03007FF0, sound_pointer)
            memory(sound, producer.memory(sound, size=0xFB0))
            io = bytearray(producer.memory(0x04000000, size=1024))
            # The producer corpus models raw PCM and starts with bare I/O.
            # Supply the real post-BIOS DAC center required by the new hardware
            # consumer; this does not alter any producer/ROM PCM8 byte.
            bias = (struct.unpack_from('<H', io, 0x88)[0] & 0xC000) | 0x0200
            struct.pack_into('<H', io, 0x88, bias)
            memory(0x04000000, bytes(io))
            assert consumer['Write'](0x88, bias, 2)
            block = producer.block()
            n = block.count
            offsets.add(block.playing_offset)
            raw.update(bytes(block.right[:n]) + bytes(block.left[:n]))
            raw.update(bytes(block.produced_right[:n]) + bytes(block.produced_left[:n]))
            consumer['VBlank']()
            assert consumer['Advance'](280896), consumer['Error']()
            chunk, count = producer.drain()
            start = len(legacy_pcm)
            assert chunk == expected[start:start + len(chunk)], ('legacy ROM corpus changed', frame)
            legacy_pcm.extend(chunk)
            if frame % 300 == 0:
                print('Passed game PCM source frames:', frame + 1, '/', frames, flush=True)
        consumer['Close']()
        actual = (out / 'game.pcm').read_bytes()
        if actual != legacy_pcm:
            first = next((i for i, pair in enumerate(zip(actual, legacy_pcm)) if pair[0] != pair[1]), min(len(actual), len(legacy_pcm)))
            raise AssertionError(dict(first_different_byte=first, stereo_sample=first // 4,
                                      actual_bytes=len(actual), expected_bytes=len(legacy_pcm),
                                      actual=actual[first:first + 16].hex(), expected=legacy_pcm[first:first + 16].hex()))
        if not args.quick:
            assert raw.hexdigest() == ref['raw_pcm_results_sha256'], 'producer PCM8 digest changed from ROM-validated corpus'
            assert hashlib.sha256(actual).hexdigest() == ref['pcm16_sha256']
        audio = json.loads((out / 'consumer_report.json').read_text())
        assert audio['ok'] and audio['clipped'] == audio['cgb_samples'] == 0
        assert audio['stereo_samples'] == len(actual) // 4
        assert not audio['device_enabled'] and not audio['whole_game_pcm_rom_equal']
        assert len(offsets) >= 2
        report = dict(frames=frames, quick=args.quick, source_song_id=ref['song_id'],
                      source_reference_report_sha256=sha(reference / 'report.json'),
                      source_pcm8_digest=raw.hexdigest(), source_pcm8_original_rom_validation_inherited=True,
                      consumer_postbios_dac_center=512,
                      new_arm_cpu_executions=0, pcm16_equal_to_immutable_rom_corpus=True,
                      stereo_samples=len(actual) // 4, pcm16_sha256=hashlib.sha256(actual).hexdigest(),
                      pcm16_fnv1a64=audio['pcm_fnv1a64'], offsets=sorted(offsets),
                      whole_game_pcm_rom_equal=False, psg_song_rom_equal=False,
                      native_build=json.loads((out / 'build.json').read_text()),
                      tool_sha256=sha(__file__), consumer_report=audio)
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print('PASS game PCM consumer:', frames, 'frames;', len(actual) // 4, 'stereo samples')
        return 0
    except Exception as error:
        consumer['Close']()
        (out / 'failed_case.json').write_text(json.dumps(dict(frame=frame, error=repr(error)), indent=2) + '\n')
        print('FAIL game PCM consumer:', repr(error))
        return 1
    finally:
        producer.close()


if __name__ == '__main__':
    raise SystemExit(main())
