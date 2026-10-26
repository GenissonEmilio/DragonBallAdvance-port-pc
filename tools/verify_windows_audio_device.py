"""Explicit, bounded WASAPI device playback and scheduler-stall validation.

Plays a quiet synthetic triangle fixture. Does not capture other applications'
audio, change device volume/settings or confirm physical speaker audibility.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
import build_windows_audio as build
ROOT=Path(__file__).resolve().parents[1]

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-dir',type=Path,default=ROOT/'build/windows_audio_device_validation')
    p.add_argument('--frames',type=int,default=1800)
    a=p.parse_args(argv)
    if not 60<=a.frames<=3000:p.error('device test must use 60..3000 frames')
    out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True);build.build(out)
    rom=ROOT/'baserom.gba'
    assert hashlib.sha1(rom.read_bytes()).hexdigest()=='1338584d8cfa57402603197e65d2e2ff0184d24f'
    reports={}
    for name,frames,stall in [('normal',a.frames,0),('injected_stall',120,50)]:
        command=[str(out/'dbaa_audio.exe'),'--rom',str(rom),'--demo','--frames',str(frames),
            '--gain','64','--report',str(out/(name+'.json'))]
        if stall:command+=['--stall-ms',str(stall)]
        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=60)
        (out/(name+'.log')).write_text(json.dumps(command)+'\n'+r.stdout+r.stderr)
        report=json.loads((out/(name+'.json')).read_text())if(out/(name+'.json')).exists()else{}
        assert r.returncode==0,(name,r.returncode,r.stdout,r.stderr,report)
        assert report['ok']and report['backend']=='wasapi_shared_event'
        assert report['frames']==frames and report['synthetic_demo']
        assert report['converted_samples']==frames*280896*48000//16777216
        assert report['consumed_samples']==report['submitted_frames']==report['converted_samples']
        assert report['faults']==report['overflow_samples']==report['underrun_samples']==0
        assert report['audio_events']>0 and report['endpoint_capacity']>0
        assert report['audio_clock_end']>report['audio_clock_start']and report['audio_clock_frequency']>0
        assert report['device_mix_rate']>0 and report['device_mix_channels']>0
        duration=report['playback_qpc']/report['qpc_frequency']
        ideal=frames*280896/16777216
        assert abs(duration-ideal)<0.2,(name,duration,ideal)
        if not stall:
            assert report['endpoint_empty_events']==0,'unexpected endpoint starvation'
        else:
            assert report['endpoint_empty_events']>0 and report['catch_up_frames']>0,'stall was not detected'
        report.update(measured_playback_seconds=duration,ideal_seconds=ideal,
            cadence_error_seconds=duration-ideal,max_late_ms=report['max_late_qpc']*1000/report['qpc_frequency'])
        reports[name]=report
        print('PASS device:',name,'frames',frames,'duration',round(duration,4),
            'seconds; endpoint empty events',report['endpoint_empty_events'],flush=True)
    result=dict(reports=reports,native_build=json.loads((out/'build.json').read_text()),
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rom_sha1=hashlib.sha1(rom.read_bytes()).hexdigest(),windows_device_api_test_passed=True,
        speaker_audibility_confirmed=False,loopback_audio_recorded=False,game_song_playback=False,
        full_game_boot=False,psg_synthesis=False,long_term_hardware_clock_drift_corrected=False)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0
if __name__=='__main__':raise SystemExit(main())
