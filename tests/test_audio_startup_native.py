"""Full GBA images and native high-level startup/Open/wrapper behavior."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class AudioStartupNativeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,
            capture_output=True,text=True,timeout=180)

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_audio_startup_complete_c_images_match(self):
        for tid,address,size in [('audio_initialize',0x10AD34,120),('audio_main',0x10ADAC,12),
            ('music_player_open',0x10B474,120)]:
            with self.subTest(target=tid),tempfile.TemporaryDirectory()as temp:
                r=self.run_tool('match.py','--target',tid,'--out-dir',temp)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                report=json.loads((Path(temp)/'report.json').read_text())
                self.assertTrue(report['equal']);self.assertEqual(report['different_bytes'],0)
                self.assertEqual(report['candidate_size'],size);self.assertFalse(report['assembly_postprocessing'])
                self.assertFalse(report['remaining_relocations'])
                self.assertEqual((Path(temp)/(tid+'.bin')).read_bytes(),(ROOT/'baserom.gba').read_bytes()[address:address+size])

    def c_mutation(self,tid,old,new):
        source=(ROOT/'src'/(tid+'.c')).read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('match.py','--target',tid,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_audio_startup_gba_copy_extent_mutation_fails_byte_gate(self):
        self.c_mutation('audio_initialize','0x04000100','0x040000FF')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_audio_wrapper_gba_callee_mutation_fails_byte_gate(self):
        self.c_mutation('audio_main','Func_0810A084();','Func_0810AD34();')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_audio_open_gba_count_mutation_fails_byte_gate(self):
        self.c_mutation('music_player_open','count > 16','count > 15')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_state_bus_chain_wrapper_and_reinitialization_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_audio_startup.py','--cases',0,'--sample-step',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],78);self.assertEqual(report['executions'],182)
            self.assertEqual(report['wrapper_updates'],96);self.assertEqual(report['lifecycle_sequences'],8)
            self.assertEqual(report['independent_oracle_executions'],86)
            self.assertEqual(report['initialized_players'],4);self.assertEqual(report['initialized_tracks'],27)
            self.assertEqual(report['copied_ram_bytes'],1024);self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['new_instruction_count'],93);self.assertEqual(report['new_instructions_covered'],93)
            self.assertEqual(report['missing_new_instructions'],[]);self.assertEqual(report['arm_fallback_targets'],[])
            self.assertEqual(set(report['reference_cpuset_controls']),{'0x4000100','0x50003ec','0x5000040','0x5000318'})
            for key in ['all_ram_equal','io_images_equal','ordered_reads_and_writes_equal',
                'independent_startup_and_open_oracle_equal','initialized_chain_executed','initialized_mixer_pcm_executed',
                'reference_bios_copy_fill_modeled']:self.assertTrue(report[key],key)
            for key in ['rom_modified','native_new_services_fallback_to_arm','reference_bios_image_used',
                'byte_matching','full_game_boot','hardware_register_side_effects_validated',
                'real_time_validated','audible_output_validated']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new,function=None):
        source=(ROOT/'port/audio/audio_helpers.c').read_text()
        begin=source.index('uint32_t '+function+'(')if function else 0
        end=source.find('\nuint32_t ',begin+1)if function else len(source)
        if end<0:end=len(source)
        fragment=source[begin:end];self.assertEqual(fragment.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source[:begin]+fragment.replace(old,new)+source[end:])
            out=Path(temp)/'out'
            r=self.run_tool('verify_audio_startup.py','--cases',0,'--sample-step',16,
                '--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr)
            self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_copy_extent_mutation_is_detected(self):
        self.native_mutation('offset < 1024','offset < 1020','Dbaa_AudioInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_copy_source_mutation_is_detected(self):
        self.native_mutation('R32(0x0810A108u + offset)','R32(0x0810A10Cu + offset)','Dbaa_AudioInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_mode_mutation_is_detected(self):
        self.native_mutation('0x0095FC00','0x0094FC00','Dbaa_AudioInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_player_count_mutation_is_detected(self):
        self.native_mutation('index < 4','index < 3','Dbaa_AudioInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_priority_width_mutation_is_detected(self):
        self.native_mutation('W8(player + 11, R16(entry + 10));','W16(player + 11, R16(entry + 10));','Dbaa_AudioInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_memory_pointer_mutation_is_detected(self):
        self.native_mutation('W32(player + 24, 0x03001EC0);','W32(player + 24, 0x03001EC4);','Dbaa_AudioInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_count_truncation_mutation_is_detected(self):
        self.native_mutation('raw_count & 255u','raw_count','Dbaa_MusicPlayerOpen')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_count_clamp_mutation_is_detected(self):
        self.native_mutation('count = 16;','count = 15;','Dbaa_MusicPlayerOpen')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_lock_mutation_is_detected(self):
        self.native_mutation('if (lock != 0x68736D53u)','if (lock == 0x68736D53u)','Dbaa_MusicPlayerOpen')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_clear_callback_mutation_is_detected(self):
        self.native_mutation('CALL(0x0810B120, player, 0, 0);','/* missing clear callback */','Dbaa_MusicPlayerOpen')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_track_stride_mutation_is_detected(self):
        self.native_mutation('tracks + index * 80u','tracks + index * 84u','Dbaa_MusicPlayerOpen')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_chain_mutation_is_detected(self):
        self.native_mutation('W32(player + 0x3C, R32(sound + 0x24));','W32(player + 0x3C, 0);','Dbaa_MusicPlayerOpen')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_wrapper_native_missing_mixer_call_is_detected(self):
        self.native_mutation('CALL(0x0810A084, 0, 0, 0);','(void)host;','Dbaa_AudioMain')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_startup_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_AudioInitialize(host);','return host->call(host->user, target, a0, a1, a2);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_wrapper_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_AudioMain(host);','return host->call(host->user, target, a0, a1, a2);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, ROM and Unicorn')
    def test_audio_open_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_MusicPlayerOpen(host, a0, a1, a2);','return host->call(host->user, target, a0, a1, a2);')


if __name__=='__main__':unittest.main()
