"""Full GBA images and native initialization, callbacks and channel setup."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class SoundInitializationNativeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_initialization_complete_c_images_match(self):
        for tid,address,size in [('sound_initialize',0x10B134,248),('sound_extend',0x10AFF0,280),('sound_dummy',0x10C224,4)]:
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
    def test_initialize_gba_dma_source_mutation_fails_byte_gate(self):
        self.c_mutation('sound_initialize','(DbaaU32)sound + 0x980','(DbaaU32)sound + 0x984')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_extend_gba_table_slot_mutation_fails_byte_gate(self):
        self.c_mutation('sound_extend','gSoundCommands[8]','gSoundCommands[9]')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_extend_gba_fill_extent_mutation_fails_byte_gate(self):
        self.c_mutation('sound_extend','0x05000040','0x05000041')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialization_native_state_bus_callbacks_and_lifecycle_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_sound_initialization.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],512);self.assertEqual(report['executions'],832)
            self.assertEqual(report['lifecycle_sequences'],32);self.assertEqual(report['lifecycle_metadata_checks'],64)
            self.assertEqual(report['installed_dummy_callback_calls'],128)
            self.assertEqual(report['original_instructions_covered'],399)
            self.assertEqual(report['initialize_instructions_covered'],89)
            self.assertEqual(report['extend_instructions_covered'],99);self.assertEqual(report['dummy_instructions_covered'],1)
            self.assertEqual(report['soundinfo_zero_fill_bytes'],4016);self.assertEqual(report['cgb_zero_fill_bytes'],256)
            self.assertEqual(report['initialized_table_bound_slots'],36);self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['installed_cgb_callbacks'],[0x0810B834,0x0810B8EC])
            self.assertEqual(report['installed_cgb_callbacks_pending_native'],[])
            self.assertEqual(set(report['reference_cpuset_controls']),{'0x5000318','0x50003ec','0x5000040'})
            self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','io_images_equal','ordered_reads_and_writes_equal','independent_model_equal',
                'full_zero_fill_extent_and_canaries_verified','fifo_dma_sources_and_widths_verified',
                'initialize_overrides_old_pointer_and_lock_verified','template_copy_and_nine_patches_verified',
                'extend_hardware_before_lock_guard_verified','cgb_fields_and_alias_order_verified',
                'global_pointer_reread_and_cached_argument_verified','lifecycle_state_carried']:self.assertTrue(report[key],key)
            for key in ['pending_cgb_callbacks_executed','native_new_services_fallback_to_arm','reference_bios_image_used',
                'byte_matching','full_game_boot','hardware_register_side_effects_validated','real_time_validated',
                'audible_output_validated']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new,function=None):
        source=(ROOT/'port/audio/audio_helpers.c').read_text()
        begin=source.index('uint32_t '+function+'(')if function else 0
        end=source.find('\nuint32_t ',begin+1)if function else len(source)
        if end<0:end=len(source)
        fragment=source[begin:end];self.assertEqual(fragment.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source[:begin]+fragment.replace(old,new)+source[end:]);out=Path(temp)/'out'
            r=self.run_tool('verify_sound_initialization.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr);self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialize_native_clear_extent_mutation_is_detected(self):
        self.native_mutation('offset < 0xFB0; offset += 4','offset < 0xFAC; offset += 4','Dbaa_SoundInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialize_native_dma_source_mutation_is_detected(self):
        self.native_mutation('W32(0x040000C8, sound + 0x980);','W32(0x040000C8, sound + 0x984);','Dbaa_SoundInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialize_native_channel_count_mutation_is_detected(self):
        self.native_mutation('W8(sound + 6, 8);','W8(sound + 6, 7);','Dbaa_SoundInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialize_native_dummy_callback_mutation_is_detected(self):
        self.native_mutation('W32(sound + 0x3C, 0x0810C225);','W32(sound + 0x3C, 0x0810AA01);','Dbaa_SoundInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialize_native_global_pointer_omission_is_detected(self):
        self.native_mutation('W32(0x03007FF0, sound);','/* missing pointer */','Dbaa_SoundInitialize')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_extend_native_hardware_write_omission_is_detected(self):
        self.native_mutation('W16(0x04000084, 0x8F);','/* missing hardware write */','Dbaa_SoundExtend')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_extend_native_hardware_width_mutation_is_detected(self):
        self.native_mutation('W16(0x04000080, 0);','W32(0x04000080, 0);','Dbaa_SoundExtend')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_extend_native_table_slot_mutation_is_detected(self):
        self.native_mutation('0x03001C70 + 8 * 4','0x03001C70 + 9 * 4','Dbaa_SoundExtend')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_extend_native_clear_extent_mutation_is_detected(self):
        self.native_mutation('offset < 0x100; offset += 4','offset < 0xFC; offset += 4','Dbaa_SoundExtend')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_extend_native_channel_mask_mutation_is_detected(self):
        self.native_mutation('W8(channels + 0xDC, 0x88);','W8(channels + 0xDC, 0x80);','Dbaa_SoundExtend')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_extend_native_lock_restore_mutation_is_detected(self):
        self.native_mutation('W32(sound, lock);','W32(sound, lock + 1u);','Dbaa_SoundExtend')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_dummy_native_arm_fallback_is_rejected(self):
        self.native_mutation('case 0x0810C224:\n    return 0;','case 0x0810C224:\n    return host->call(host->user, target, a0, a1, a2);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_initialize_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_SoundInitialize(host, a0);','return host->call(host->user, target, a0, a1, a2);')


if __name__=='__main__':unittest.main()
