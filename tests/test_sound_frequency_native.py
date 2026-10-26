"""Complete GBA images and native frequency setup, timer and VCOUNT integration."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class SoundFrequencyNativeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_sound_frequency_and_vsync_complete_c_images_match(self):
        for tid,address,size in [('sound_set_frequency',0x10B22C,164),('sound_vsync_on',0x10B438,60)]:
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
    def test_frequency_gba_mode_mask_mutation_fails_byte_gate(self):
        self.c_mutation('sound_set_frequency','input & 0xF0000','input & 0x70000')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_frequency_gba_timer_mutation_fails_byte_gate(self):
        self.c_mutation('sound_set_frequency','280896 / samples','280895 / samples')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_vsync_gba_dma_mutation_fails_byte_gate(self):
        self.c_mutation('sound_vsync_on','IO16(0x040000C6) = 0xB600;','IO16(0x040000C6) = 0xB601;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_state_bus_clock_and_consecutive_calls_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_sound_frequency.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],1222);self.assertEqual(report['executions'],1254)
            self.assertEqual(report['consecutive_sequences'],32);self.assertEqual(report['original_instructions_covered'],81)
            self.assertEqual(report['frequency_mode_nibbles_tested'],16);self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','io_images_equal','ordered_reads_and_writes_equal','independent_model_equal',
                'mode_mask_ignored_bits_verified','signed_division_and_32bit_multiply_wrap_verified',
                'reciprocal_arithmetic_shift_verified','timer_halfword_width_and_order_verified','leave_then_enter_vcount_verified',
                'vsync_magic_guard_and_lock_wrap_verified','volatile_unknown04_read_verified','sound_pointer_reread_verified',
                'original_callee_saved_registers_preserved']:self.assertTrue(report[key],key)
            for key in ['native_new_services_fallback_to_arm','byte_matching','full_game_boot',
                'hardware_register_side_effects_validated','real_time_validated','audible_output_validated']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_sound_frequency.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr);self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_mask_mutation_is_detected(self):
        self.native_mutation('uint32_t index = (mode >> 16) & 15u;','uint32_t index = (mode >> 16) & 7u;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_multiply_wrap_mutation_is_detected(self):
        self.native_mutation('uint32_t rate = sound_divide(597275u * samples + 5000u, 10000u);',
            'uint32_t rate = (uint32_t)(((uint64_t)597275u * samples + 5000u) / 10000u);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_rate_rounding_mutation_is_detected(self):
        self.native_mutation('597275u * samples + 5000u','597275u * samples + 0u')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_reciprocal_shift_mutation_is_detected(self):
        self.native_mutation('(reciprocal >> 1) | (reciprocal & 0x80000000u)','reciprocal >> 1')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_timer_width_mutation_is_detected(self):
        self.native_mutation('W16(0x04000102, 0);','W32(0x04000102, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_leave_line_wait_mutation_is_detected(self):
        self.native_mutation('while (R8(0x04000006) == 159u)\n    ;','/* incorrect: skip leaving line 159 */')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_vsync_native_guard_mutation_is_detected(self):
        prefix='uint32_t Dbaa_SoundVSyncOn(const DbaaMusicHost *host) {\n  uint32_t sound = R32(0x03007FF0);\n  uint32_t lock = R32(sound);\n'
        self.native_mutation(prefix+'  if (lock != 0x68736D53u) {',prefix+'  if (lock == 0x68736D53u) {')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_vsync_native_volatile_read_mutation_is_detected(self):
        self.native_mutation('(void)R8(sound + 4);','/* incorrect: omit volatile read */')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_vsync_native_lock_wrap_mutation_is_detected(self):
        self.native_mutation('W32(sound, lock - 10u);','W32(sound, lock + 10u);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_frequency_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_SoundSetFrequency(host, a0);','return host->call(host->user, target, a0, a1, a2);')


if __name__=='__main__':unittest.main()
