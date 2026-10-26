"""Compare original-ROM and native music-driver state for songs using CGB.

This uses the original isolated flat-I/O driver oracle, not a full GBA boot.
It compares software state, ordered bus operations and PCM8 producer buffers.
PSG waveform synthesis is validated separately; no full mixed-PCM claim here.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import struct
import verify_song_playback as songs
import verify_windows_audio as windows
import verify_pcm_mixer as mixer
import verify_audio_startup as startup
import verify_sound_frequency as frequency

ROOT = Path(__file__).resolve().parents[1]
SONGS = [4, 7, 11, 13, 14, 16, 19, 21, 23]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'build/native_cgb_song_validation')
    parser.add_argument('--frames', type=int, default=1800)
    parser.add_argument('--songs', type=int, nargs='+', default=SONGS)
    args = parser.parse_args()
    assert args.frames >= 120
    assert len(args.songs) == len(set(args.songs)) and set(args.songs) <= set(SONGS)
    out = args.out_dir.resolve()
    assert not out.exists(), 'preserve previous evidence; use a new output directory'
    out.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    frozen = ROOT / 'build/native_song_validation'
    reference = json.loads((frozen / 'report.json').read_text())
    build = reference['native_build']
    assert build['dll_sha256'] == sha(frozen / 'audio_runtime.dll')
    assert all(sha(ROOT / p) == h for p, h in build['sources_sha256'].items())
    dll = ctypes.CDLL(str(frozen / 'audio_runtime.dll'))
    rt = windows.Runtime(dll)
    songs.bind(rt)
    catalog = songs.catalog()
    results = []
    try:
        for song_id in args.songs:
            # Choose a window that actually reaches this song's CGB passage
            # before stopping/restarting it. The subsequent ROM run verifies
            # that this native-only scouting prediction was correct.
            scout = windows.Runtime(dll)
            songs.bind(scout)
            first_cgb = None
            try:
                scout.reset()
                scout.Observe(scout.r, windows.OBS(), None)
                assert scout.StartSong(scout.r, song_id)
                for i in range(7200):
                    assert scout.Frame(scout.r), scout.Error(scout.r)
                    scout.drain()
                    if scout.stats().cgb_active_frames:
                        first_cgb = i
                        break
            finally:
                scout.close()
            assert first_cgb is not None, 'no CGB passage found in native scout'
            stop_frame = max(args.frames // 3, first_cgb + 60)
            frames = max(args.frames, stop_frame + 8 + first_cgb + 120)
            rt.reset()
            before_cgb = rt.stats().cgb_active_frames
            rt.filter = songs.watched
            rt.Observe(rt.r, rt.observer, None)
            original = songs.RomEngine(rt.images(), set())
            raw = hashlib.sha256()
            state = hashlib.sha256()
            bus = hashlib.sha256()
            active = 0
            first_original_cgb = None
            channel_active = [0] * 4
            actions = {0: ('start', song_id), stop_frame: ('stop', catalog[song_id]['player']),
                       stop_frame + 8: ('start', song_id), frames - 8: ('all', 0)}
            for frame in range(frames):
                original.trace = []
                rt.trace = []
                if frame in actions:
                    action, value = actions[frame]
                    if action == 'start':
                        assert rt.StartSong(rt.r, value)
                        original.invoke(songs.START_SONG, value)
                    elif action == 'stop':
                        assert rt.StopPlayer(rt.r, value)
                        original.invoke(songs.STOP, startup.PLAYERS[value][0])
                    else:
                        assert rt.StopAll(rt.r)
                        original.invoke(songs.STOP_ALL)
                    songs.assert_equal(original.images(), rt.images(), original.trace, rt.trace,
                                       f'song {song_id} action {frame}')
                    original.trace = []
                    rt.trace = []
                assert rt.Frame(rt.r), rt.Error(rt.r)
                original.invoke(windows.VBLANK)
                original.invoke(startup.WRAPPER)
                images = original.images()
                songs.assert_equal(images, rt.images(), original.trace, rt.trace, f'song {song_id} frame {frame}')
                block = rt.block()
                n = block.count
                counter = mixer.get(images, startup.init.SOUND + 4)
                period = mixer.get(images, startup.init.SOUND + 11)
                playing = (period - counter) * n
                produced = (period - counter + 1) * n if counter > 1 else 0
                assert (block.playing_offset, block.produced_offset) == (playing, produced)
                for offset, right, left in [(playing, block.right, block.left),
                                            (produced, block.produced_right, block.produced_left)]:
                    for side, data in [(0, right), (1, left)]:
                        expected = bytes(mixer.get(images, startup.init.SOUND + 0x350 + side * 0x630 + offset + j)
                                         for j in range(n))
                        assert expected == bytes(data[:n]), 'PCM8 producer buffer differs'
                        raw.update(expected)
                pointer = mixer.get(images, startup.init.SOUND + 28, 4)
                live = [bool(mixer.get(images, pointer + i * 64) & 0xC7) for i in range(4)]
                if any(live) and first_original_cgb is None:
                    first_original_cgb = frame
                active += any(live)
                channel_active = [a + b for a, b in zip(channel_active, live)]
                state.update(frequency.comparable(images))
                for kind, address, width, value in original.trace:
                    bus.update(struct.pack('<BIBI', kind == 'write', address, width, value))
                rt.drain()  # Discard the old PCM-only converter, which has no PSG.
            stats = rt.stats()
            assert stats.faults == stats.overflow_samples == stats.underrun_samples == 0
            assert active > 0 and active == stats.cgb_active_frames - before_cgb, 'CGB coverage counters differ'
            assert first_original_cgb == first_cgb, 'original ROM disagrees with native CGB activation scout'
            result = dict(song_id=song_id, frames=frames, requested_frames=args.frames, actions=actions,
                          native_scout_first_cgb_frame=first_cgb, original_first_cgb_frame=first_original_cgb,
                          cgb_active_frames=active, channel_active_frames=channel_active,
                          state_sha256=state.hexdigest(), bus_sha256=bus.hexdigest(),
                          pcm8_sha256=raw.hexdigest(), state_equal=True, ordered_bus_equal=True,
                          pcm8_buffers_equal=True, original_rom_executed=True, native_arm_fallback=False)
            results.append(result)
            (out / f'song_{song_id:03d}.json').write_text(json.dumps(result, indent=2) + '\n')
            print('Passed original CGB song', song_id, frames, 'frames; active', active, flush=True)
    except Exception as exc:
        (out / 'failure.json').write_text(json.dumps(dict(song_id=song_id, frame=frame, error=repr(exc)), indent=2) + '\n')
        raise
    finally:
        rt.close()
    report = dict(songs=results, frames=sum(r['frames'] for r in results),
                  rom_sha1=reference['rom_sha1'], native_dll_sha256=sha(frozen / 'audio_runtime.dll'),
                  inherited_build_sha256=sha(frozen / 'build.json'), tool_sha256=sha(__file__),
                  software_state_and_bus_equal=True, pcm8_producer_equal=True,
                  reference_model='isolated driver with flat audio I/O',
                  psg_synthesis_compared=False, whole_game_pcm_rom_equal=False,
                  full_game_boot=False, gba_byte_matching=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
