"""Join completed song corpora while preserving two earlier coverage failures."""
from pathlib import Path
import hashlib
import json

ROOT = Path.cwd()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())


def main():
    groups = [('native_cgb_song_validation', [4, 7, 11, 13], 1200),
              ('native_cgb_song_remaining_validation', [14, 16], 1800),
              ('native_cgb_song_final_validation', [19, 21, 23], None)]
    rows, reports = [], {}
    for folder, song_ids, frames in groups:
        directory = ROOT / 'build' / folder
        if frames is not None:
            metadata = read(directory / 'attempt_metadata.json')
            assert sha(directory / 'tool_snapshot.py') == metadata['tool_sha256']
            assert metadata['passed_partial_songs'] == song_ids
            assert 'did not exercise CGB channels' in read(directory / 'failure.json')['error']
            source_digest = metadata['tool_sha256']
        else:
            complete = read(directory / 'report.json')
            assert complete['tool_sha256'] == sha(ROOT / 'tools/verify_cgb_songs.py')
            assert complete['reference_model'] == 'isolated driver with flat audio I/O'
            assert complete['software_state_and_bus_equal'] and complete['pcm8_producer_equal']
            assert not complete['psg_synthesis_compared'] and not complete['whole_game_pcm_rom_equal']
            source_digest = complete['tool_sha256']
        for song_id in song_ids:
            path = directory / f'song_{song_id:03d}.json'
            song = read(path)
            assert song['song_id'] == song_id and song['cgb_active_frames'] > 0
            assert song['state_equal'] and song['ordered_bus_equal'] and song['pcm8_buffers_equal']
            assert song['original_rom_executed'] and not song['native_arm_fallback']
            if frames:
                assert song['frames'] == frames
            else:
                assert song['native_scout_first_cgb_frame'] == song['original_first_cgb_frame']
            rows.append(song)
            reports[str(path.relative_to(ROOT))] = dict(sha256=sha(path), tool_sha256=source_digest)
    assert sorted(s['song_id'] for s in rows) == [4, 7, 11, 13, 14, 16, 19, 21, 23]
    assert sum(s['frames'] for s in rows) == 14892
    song_dir = ROOT / 'build/native_song_validation'
    build = read(song_dir / 'build.json')
    assert sha(song_dir / 'audio_runtime.dll') == build['dll_sha256']
    assert all(sha(ROOT / p) == h for p, h in build['sources_sha256'].items())
    out = ROOT / 'build/native_cgb_song_combined_validation'
    out.mkdir(exist_ok=True)
    report = dict(song_ids=sorted(s['song_id'] for s in rows), frames=14892,
                  cgb_active_frames=sum(s['cgb_active_frames'] for s in rows),
                  state_equal=True, ordered_bus_equal=True, pcm8_producer_buffers_equal=True,
                  original_rom_executed=True, native_arm_fallback=False,
                  reference_model='isolated driver with flat audio I/O',
                  psg_synthesis_compared=False, whole_game_pcm_rom_equal=False,
                  earlier_coverage_failures_preserved=True, full_game_boot=False,
                  native_build_sha256=sha(song_dir / 'build.json'), native_dll_sha256=sha(song_dir / 'audio_runtime.dll'),
                  tool_sha256=sha(__file__), songs=rows, reports=reports)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    previous = ROOT / 'build/next/clean_game/audit.json'
    verification = read(previous)
    assert verification['stage'] == 'source_build_and_asynchronous_win32_presentation'
    assert not verification['port_complete'] and verification['source_build_objects'] == 108
    assert verification['canonical_build_sha256'] == sha(ROOT / 'build/windows_native/build.json')
    verification.update(stage='source_build_async_window_and_nine_cgb_driver_rom_corpora',
                        previous_audit_sha256=sha(previous), cgb_driver_songs=9,
                        cgb_driver_rom_frames=14892, cgb_software_state_bus_pcm8_equal=True,
                        cgb_reference_model=report['reference_model'], cgb_psg_mix_rom_equal=False,
                        cgb_report_sha256=sha(out / 'report.json'))
    (ROOT / 'build/verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print('AUDIT OK: nine CGB songs,14892 original-ROM driver frames; state/bus/PCM8 equal. Full PSG mix is not this oracle.')


if __name__ == '__main__':
    main()
