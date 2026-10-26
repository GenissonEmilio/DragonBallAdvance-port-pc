"""Play the ROM-validated original song over WASAPI and verify submitted PCM."""
from pathlib import Path
import argparse,hashlib,json,subprocess,wave
import build_windows_audio as build
import verify_song_playback as songs
ROOT=Path(__file__).resolve().parents[1]


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,default=ROOT/'build/native_song_validation')
    p.add_argument('--out-dir',type=Path,default=ROOT/'build/song_device_validation')
    a=p.parse_args(argv);out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    (out/'report.json').unlink(missing_ok=True)
    ref=json.loads((a.reference/'report.json').read_text())
    assert not ref['quick'] and ref['original_song_frames']<=3000
    assert ref['pcm8_bytes_equal']and ref['pcm16_timestamp_oracle_equal']and ref['no_native_arm_fallback']
    assert ref['rom_sha1']==hashlib.sha1((ROOT/'baserom.gba').read_bytes()).hexdigest()
    assert ref['tool_sha256']==sha(songs.__file__)
    assert all(sha(ROOT/p)==h for p,h in ref['native_build']['sources_sha256'].items())
    build.build(out)
    options=['--rom',str(ROOT/'baserom.gba'),'--song',str(ref['song_id']),
             '--frames',str(ref['original_song_frames']),'--gain','64']
    for frame,(action,value)in ref['actions'].items():
        if action=='start'and int(frame)==0:continue
        flag={'start':'--restart-at','player_stop':'--stop-at','global_stop':'--stop-all-at'}[action]
        options.extend([flag,frame])
    reports={}
    for name,extra in [('offline',['--wav',str(out/'song.wav')]),('wasapi',[])]:
        command=[str(out/'dbaa_audio.exe'),*options,*extra,'--report',str(out/(name+'.json'))]
        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=65)
        (out/(name+'.log')).write_text(json.dumps(command)+'\n'+r.stdout+r.stderr)
        assert r.returncode==0,(name,r.returncode,r.stdout,r.stderr)
        data=json.loads((out/(name+'.json')).read_text())
        assert data['ok']and not data['synthetic_demo']
        assert data['song_id']==ref['song_id']and data['frames']==ref['original_song_frames']
        assert data['source_samples']==ref['source_stereo_samples']
        assert data['converted_samples']==data['consumed_samples']==ref['host_stereo_samples']
        assert data['consumed_pcm_fnv1a64']==ref['pcm16_fnv1a64'],'submitted PCM differs from ROM-derived PCM'
        assert data['faults']==data['overflow_samples']==data['underrun_samples']==0
        assert data['cgb_active_frames']==ref['cgb_active_frames']==0,'selected song requires missing PSG synthesis'
        if name=='offline':
            with wave.open(str(out/'song.wav'))as wav:
                assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(2,2,48000)
                pcm=wav.readframes(wav.getnframes())
            assert hashlib.sha256(pcm).hexdigest()==ref['pcm16_sha256']
            assert songs.fnv(pcm)==data['consumed_pcm_fnv1a64']
        else:
            assert data['backend']=='wasapi_shared_event'
            assert data['submitted_frames']==data['converted_samples']and data['audio_events']>0
            assert data['audio_clock_end']>data['audio_clock_start']
            assert data['endpoint_empty_events']==0
            duration=data['playback_qpc']/data['qpc_frequency']
            ideal=ref['original_song_frames']*280896/16777216
            assert abs(duration-ideal)<0.2
            data.update(measured_seconds=duration,ideal_seconds=ideal,
                max_late_ms=data['max_late_qpc']*1000/data['qpc_frequency'])
        reports[name]=data
        print('PASS original song:',name,ref['song_id'],data['frames'],'frames',flush=True)
    report=dict(reports=reports,native_build=json.loads((out/'build.json').read_text()),
        tool_sha256=sha(__file__),reference_tool_sha256=sha(songs.__file__),
        reference_report_sha256=sha(a.reference/'report.json'),reference_directory=str(a.reference.resolve()),
        reference_pcm_sha256=ref['pcm16_sha256'],song_id=ref['song_id'],rom_sha1=ref['rom_sha1'],
        submitted_pcm_equals_rom_derived_pcm=True,original_song_played_via_wasapi=True,
        speaker_audibility_confirmed=False,loopback_recorded=False,analog_output_bit_exact=False,
        full_game_boot=False,psg_synthesis=False,long_term_hardware_clock_drift_corrected=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0
if __name__=='__main__':raise SystemExit(main())
