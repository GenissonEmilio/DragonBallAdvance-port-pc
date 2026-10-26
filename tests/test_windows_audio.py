"""Windows audio host PCM, buffering, deadline and output-file regression gates."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest,wave,array
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()and importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(READY,'requires native Windows toolchain, ROM and Unicorn')
class WindowsAudioTests(unittest.TestCase):
    def run_tool(self,*args):
        return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)
    def test_windows_audio_pcm_ram_bus_pipeline_and_timestamp_oracle(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('tools/verify_windows_audio.py','--quick','--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['sequences'],1);self.assertEqual(report['game_frames'],4)
            self.assertEqual(report['source_samples'],1056);self.assertEqual(report['host_stereo_samples'],3214)
            self.assertEqual(report['vsync_cases'],64);self.assertEqual(report['vsync_instructions_covered'],33)
            self.assertEqual(report['virtual_long_run_frames'],200)
            self.assertEqual(report['virtual_long_run_samples'],200*280896*48000//16777216)
            for key in ['pcm_bytes_equal','ram_io_equal','ordered_bus_equal','fifo_one_block_pipeline_equal',
                'pcm16_timestamp_oracle_equal','no_native_arm_fallback','ring_overflow_rejected','ring_underflow_zero_filled']:
                self.assertTrue(report[key],key)
            for key in ['full_game_boot','psg_synthesis','analog_output_bit_exact','physical_audibility_confirmed',
                'windows_device_test_included','byte_matching']:self.assertFalse(report[key],key)

    def mutation(self,old,new):
        source=(ROOT/'port/native/audio_runtime.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('tools/verify_windows_audio.py','--quick','--runtime-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists())
            self.assertFalse((out/'report.json').exists())
    def test_windows_audio_counter_mutation_is_detected(self):
        self.mutation('(int)R(sound + 4, 1) - 1','(int)R(sound + 4, 1) - 2')
    def test_windows_audio_dma_block_mutation_is_detected(self):
        self.mutation('(period - counter) * count','(period - counter + 1) * count')
    def test_windows_audio_channel_swap_is_detected(self):
        self.mutation('r->ring[tail][0] = output_sample(left, r->gain);','r->ring[tail][0] = output_sample(right, r->gain);')
    def test_windows_audio_resampler_clock_mutation_is_detected(self):
        self.mutation('r->phase += (uint64_t)ticks * DBAA_OUTPUT_HZ;','r->phase += (uint64_t)ticks * (DBAA_OUTPUT_HZ + 1);')
    def test_windows_audio_vblank_dma_width_mutation_is_detected(self):
        self.mutation('W(0x040000C6, 0xB600, 2);','W(0x040000C6, 0xB600, 4);')
    def test_windows_audio_absolute_deadline_mutation_is_detected(self):
        self.mutation('(cycles % DBAA_CPU_HZ) * frequency / DBAA_CPU_HZ',
            '(cycles % DBAA_CPU_HZ) * frequency / (DBAA_CPU_HZ + 1)')
    def test_windows_audio_underflow_mutation_is_detected(self):
        self.mutation('memset(out + 2 * actual, 0,','memset(out + 2 * actual, 1,')

    def test_windows_audio_offline_runner_wav_contains_pcm(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp)
            r=self.run_tool('tools/build_windows_audio.py','--out-dir',root)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            wav=root/'sample.wav';report=root/'run.json'
            r=subprocess.run([str(root/'dbaa_audio.exe'),'--rom',str(ROOT/'baserom.gba'),
                '--demo','--frames','8','--wav',str(wav),'--report',str(report)],
                cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            data=json.loads(report.read_text())
            self.assertTrue(data['ok']);self.assertEqual(data['backend'],'offline_wav')
            self.assertEqual(data['converted_samples'],8*280896*48000//16777216)
            self.assertEqual(data['consumed_samples'],data['converted_samples'])
            self.assertEqual(data['underrun_samples'],0);self.assertEqual(data['overflow_samples'],0)
            with wave.open(str(wav))as f:
                self.assertEqual((f.getnchannels(),f.getsampwidth(),f.getframerate()),(2,2,48000))
                self.assertEqual(f.getnframes(),data['converted_samples'])
                samples=array.array('h',f.readframes(f.getnframes()))
            self.assertLess(min(samples),0);self.assertGreater(max(samples),0)
            self.assertEqual(samples[:2*803],array.array('h',[0]*(2*803)))

    def test_windows_audio_cli_rejects_bad_rom_and_arguments(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);r=self.run_tool('tools/build_windows_audio.py','--out-dir',root)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            bad=root/'bad.gba';bad.write_bytes(bytes(16))
            for args in [['--rom',str(bad)],['--mode','0'],['--gain','257'],['--frames','0'],['--frames','abc']]:
                with self.subTest(args=args):
                    r=subprocess.run([str(root/'dbaa_audio.exe'),*args],cwd=ROOT,
                        capture_output=True,text=True,timeout=30)
                    self.assertEqual(r.returncode,2,r.stdout+r.stderr)


if __name__=='__main__':unittest.main()
