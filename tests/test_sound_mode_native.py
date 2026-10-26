"""Exact GBA images and native mode/VSync-off state, DMA and PCM integration."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class SoundModeNativeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_mode_and_off_complete_c_images_match(self):
        for tid,address,size in [('audio_mode',0x10B2D0,152),('sound_vsync_off',0x10B3BC,124)]:
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
            self.assertEqual(r.returncode,1,r.stdout+r.stderr);self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_mode_gba_channel_count_mutation_fails_byte_gate(self):
        self.c_mutation('audio_mode','temp=12;','temp=11;')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_mode_gba_bias_gate_mutation_fails_byte_gate(self):
        self.c_mutation('audio_mode','mode&0xb00000','mode&0x300000')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_off_gba_cpuset_count_mutation_fails_byte_gate(self):
        self.c_mutation('sound_vsync_off','0x05000318','0x05000319')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_state_bus_pcm_cycles_and_nested_calls_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_sound_mode.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],1218);self.assertEqual(report['executions'],1314)
            self.assertEqual(report['stop_resume_reconfigure_cycles'],32);self.assertEqual(report['original_instructions_covered'],195)
            self.assertEqual(report['mode_instructions_covered'],68);self.assertEqual(report['off_instructions_covered'],46)
            self.assertEqual(report['pcm_fill_words'],792);self.assertEqual(report['pcm_fill_bytes'],3168)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','io_images_equal','ordered_reads_and_writes_equal','independent_model_equal',
                'zero_mode_fields_preserved','reverb_enable_bit_and_mask_verified','twelve_channel_status_bytes_only_verified',
                'bias_flag_gate_and_low_bits_verified','dma_word_conditional_and_halfword_order_verified',
                'pcm_fill_extent_width_and_canaries_verified','off_unsigned_lock_guard_verified','nested_frequency_chain_verified',
                'original_mode_lock_restored_verified','sound_pointer_reread_verified','stop_resume_reconfigure_state_carried',
                'original_callee_saved_registers_preserved']:self.assertTrue(report[key],key)
            for key in ['native_new_services_fallback_to_arm','reference_bios_image_used','byte_matching','full_game_boot',
                'hardware_register_side_effects_validated','real_time_validated','audible_output_validated']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new,function=None):
        source=(ROOT/'port/audio/audio_helpers.c').read_text()
        begin=source.index('uint32_t '+function+'(')if function else 0
        end=source.find('\nuint32_t ',begin+1)if function else len(source)
        if end<0:end=len(source)
        fragment=source[begin:end];self.assertEqual(fragment.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source[:begin]+fragment.replace(old,new)+source[end:]);out=Path(temp)/'out'
            r=self.run_tool('verify_sound_mode.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr);self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_reverb_enable_mask_mutation_is_detected(self):
        self.native_mutation('W8(sound + 5, value & 0x7Fu);','W8(sound + 5, value & 0xFFu);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_zero_field_mutation_is_detected(self):
        self.native_mutation('if (value)\n    W8(sound + 5, value & 0x7Fu);','W8(sound + 5, value & 0x7Fu);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_channel_count_mutation_is_detected(self):
        self.native_mutation('channel < 12; ++channel','channel < 11; ++channel')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_bias_gate_mutation_is_detected(self):
        self.native_mutation('value = mode & 0xB00000u;','value = mode & 0x300000u;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_bias_low_bits_mutation_is_detected(self):
        self.native_mutation('uint32_t bias = R8(0x04000089) & 0x3Fu;','uint32_t bias = R8(0x04000089) & 0x00u;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_off_native_dma_condition_mutation_is_detected(self):
        self.native_mutation('if (R32(0x040000C4) & 0x02000000u)','if (R32(0x040000C4) & 0x04000000u)','Dbaa_SoundVSyncOff')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_off_native_lock_guard_mutation_is_detected(self):
        self.native_mutation('if (lock - 0x68736D53u > 1u)','if (lock - 0x68736D53u > 0u)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_off_native_dma_width_mutation_is_detected(self):
        self.native_mutation('W16(0x040000C6, 0x400);','W32(0x040000C6, 0x400);','Dbaa_SoundVSyncOff')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_off_native_pcm_extent_mutation_is_detected(self):
        self.native_mutation('offset < 0xC60; offset += 4','offset < 0xC5C; offset += 4')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_off_native_pcm_destination_mutation_is_detected(self):
        self.native_mutation('W32(sound + 0x350 + offset, 0);','W32(sound + 0x354 + offset, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_frequency_order_mutation_is_detected(self):
        self.native_mutation('CALL(0x0810B3BC, 0, 0, 0);\n    CALL(0x0810B22C, value, 0, 0);',
            'CALL(0x0810B22C, value, 0, 0);\n    CALL(0x0810B3BC, 0, 0, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_mode_native_lock_restore_mutation_is_detected(self):
        self.native_mutation('W32(sound, 0x68736D53u);','W32(sound, lock + 1u);','Dbaa_SoundMode')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_off_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_SoundVSyncOff(host);','return host->call(host->user, target, a0, a1, a2);')


if __name__=='__main__':unittest.main()
