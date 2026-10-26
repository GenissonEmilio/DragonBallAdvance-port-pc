"""Real song start/stop, priority, ordered reads and ROM-derived PCM gates."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest,wave,array
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()and importlib.util.find_spec('unicorn')is not None


@unittest.skipUnless(READY,'requires Windows toolchain, ROM and Unicorn')
class SongPlaybackTests(unittest.TestCase):
    def run_tool(self,*args):
        return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)
    def test_real_song_api_priority_stop_restart_bus_and_pcm(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('tools/verify_song_playback.py','--quick','--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            data=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(data['api_cases'],56);self.assertEqual(data['song_table_entries'],970)
            self.assertEqual(data['original_song_frames'],80);self.assertEqual(data['source_stereo_samples'],21120)
            self.assertEqual(data['host_stereo_samples'],80*280896*48000//16777216)
            self.assertEqual(data['api_instructions_covered'],data['api_instruction_count'])
            self.assertEqual(len(data['native_audio_targets']),66)
            self.assertEqual(data['cgb_active_frames'],0)
            for key in['pcm8_bytes_equal','pcm16_timestamp_oracle_equal','ram_io_equal','ordered_bus_equal','no_native_arm_fallback']:
                self.assertTrue(data[key],key)
            for key in['byte_matching','full_game_boot','psg_synthesis','analog_output_bit_exact']:
                self.assertFalse(data[key],key)

    def mutation(self,old,new,player=False):
        source=(ROOT/('port/audio/music_player_update.c'if player else'port/audio/audio_helpers.c')).read_text()
        self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new))
            out=Path(temp)/'out'
            r=self.run_tool('tools/verify_song_playback.py','--quick',
                '--player-source'if player else'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())
    def test_song_table_stride_mutation_detected(self):
        self.mutation('(song & 65535u) * 8u','(song & 65535u) * 4u')
    def test_song_equal_priority_rejection_detected(self):
        self.mutation('if (R8(player + 9) > priority)','if (R8(player + 9) >= priority)')
    def test_song_track_initialization_mutation_detected(self):
        self.mutation('W8(track, 0xC0);','W8(track, 0x80);')
    def test_song_stop_mask_mutation_detected(self):
        self.mutation('W32(player + 4, R32(player + 4) | 0x80000000u);','W32(player + 4, R32(player + 4) | 0x40000000u);')
    def test_song_stop_all_missing_player_detected(self):
        self.mutation('Dbaa_MusicPlayerStop(host, R32(0x08A69038u + i * 12u));',
                      'if (i != 3) Dbaa_MusicPlayerStop(host, R32(0x08A69038u + i * 12u));')
    def test_real_song_priority_read_order_regression_detected(self):
        self.mutation('uint32_t priority = R8(player + 9);\n  priority += R8(track + 0x1D);',
                      'uint32_t priority = R8(track + 0x1D);\n  priority += R8(player + 9);')
    def test_real_song_volume_status_reload_regression_detected(self):
        self.mutation('status = R8(track);\n  if (status & 4)', '/* missing reload */\n  if (status & 4)')
    def test_player_lfo_speed_extra_read_regression_detected(self):
        self.mutation('uint32_t phase = R8(track + 0x1A) + speed;',
                      'uint32_t phase = R8(track + 0x1A) + R8(track + 0x19);',True)
    def test_player_channel_volume_read_write_order_regression_detected(self):
        self.mutation('W8(channel + 2, right > 255 ? 255 : right);\n  uint32_t left = ((uint32_t)(127 - pan) * velocity * R8(track + 0x11)) >> 14;',
                      'uint32_t left = ((uint32_t)(127 - pan) * velocity * R8(track + 0x11)) >> 14;\n  W8(channel + 2, right > 255 ? 255 : right);',True)
    def test_player_cgb_pitch_callback_read_order_regression_detected(self):
        self.mutation('uint32_t callback = R32(sound + 0x30);\n              uint32_t fine = R8(track + 9);',
                      'uint32_t fine = R8(track + 9);\n              uint32_t callback = R32(sound + 0x30);',True)

    def test_cli_song_controls_match_rom_reference_pcm(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp)
            r=self.run_tool('tools/verify_song_playback.py','--quick','--out-dir',out)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            wav=out/'cli.wav';report=out/'cli.json'
            r=subprocess.run([str(out/'dbaa_audio.exe'),'--rom',str(ROOT/'baserom.gba'),
                '--song','1','--frames','80','--stop-at','60','--restart-at','64','--stop-all-at','72',
                '--wav',str(wav),'--report',str(report)],cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            data=json.loads(report.read_text());ref=json.loads((out/'report.json').read_text())
            self.assertEqual(data['song_id'],1);self.assertEqual(data['song_player_index'],0)
            self.assertEqual(data['consumed_pcm_fnv1a64'],ref['pcm16_fnv1a64'])
            with wave.open(str(wav))as f:pcm=f.readframes(f.getnframes())
            self.assertEqual(pcm,(out/'song_reference.pcm').read_bytes())

    def test_cli_song_controls_reject_invalid_arguments(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);r=self.run_tool('tools/build_windows_audio.py','--out-dir',out)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            for options in[['--song','970'],['--song','-1'],['--song','abc'],['--song','1','--demo'],
                            ['--restart-at','10'],['--stop-at','10'],['--song','1','--stop-at','abc']]:
                with self.subTest(options=options):
                    r=subprocess.run([str(out/'dbaa_audio.exe'),*options],cwd=ROOT,capture_output=True,text=True,timeout=30)
                    self.assertEqual(r.returncode,2,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
