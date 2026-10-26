"""CGB complete GBA images and native envelopes, wave RAM, routing and callbacks."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class CgbNativeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=180)

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_cgb_complete_c_images_match(self):
        for tid,address,size in [('cgb_stop',0x10B834,80),('cgb_update_volume',0x10B884,104),('cgb_update',0x10B8EC,1100)]:
            with self.subTest(target=tid),tempfile.TemporaryDirectory()as temp:
                r=self.run_tool('match.py','--target',tid,'--out-dir',temp)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr);report=json.loads((Path(temp)/'report.json').read_text())
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
    def test_cgb_stop_gba_register_mutation_fails_byte_gate(self):
        self.c_mutation('cgb_stop','0x04000063','0x04000062')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_cgb_volume_gba_rounding_mutation_fails_byte_gate(self):
        self.c_mutation('cgb_update_volume','* volume + 15','* volume + 14')

    @unittest.skipUnless(READY,'requires ROM and GBA compiler')
    def test_cgb_update_gba_counter_mutation_fails_byte_gate(self):
        self.c_mutation('cgb_update','a = (14);','a = (13);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_native_state_bus_installed_callbacks_and_track_stop_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_cgb.py','--cases',0,'--sample-step',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr);report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],492);self.assertEqual(report['executions'],700)
            self.assertEqual(report['routes']['guards'],21);self.assertEqual(report['routes']['track_stop'],16)
            self.assertEqual(report['lifecycle_sequences'],8);self.assertEqual(report['installed_callback_calls'],200)
            self.assertEqual(report['installed_update_frames'],192);self.assertGreaterEqual(report['cgb_instructions_covered'],560)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['arm_fallback_targets'],[])
            self.assertEqual(report['cgb_callbacks_pending_native'],[])
            self.assertGreater(report['observed_wave_ram_writes'],0)
            for key in ['all_ram_equal','io_images_equal','ordered_reads_and_writes_equal','independent_model_equal',
                'cgb_callbacks_executed','stop_update_volume_in_c']:self.assertTrue(report[key],key)
            for key in ['native_cgb_fallback_to_arm','byte_matching','full_game_boot','hardware_register_side_effects_validated',
                'real_time_validated','audible_output_validated','reference_bios_image_used']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new,function=None):
        source=(ROOT/'port/audio/audio_helpers.c').read_text()
        begin=source.index('uint32_t '+function+'(')if function else 0
        end=source.find('\nuint32_t ',begin+1)if function else len(source)
        if end<0:end=len(source)
        fragment=source[begin:end];self.assertEqual(fragment.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source[:begin]+fragment.replace(old,new)+source[end:]);out=Path(temp)/'out'
            r=self.run_tool('verify_cgb.py','--cases',0,'--sample-step',16,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr);self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_stop_native_argument_byte_mutation_is_detected(self):
        self.native_mutation('switch (channel & 255)','switch (channel)','Dbaa_CgbStop')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_stop_native_width_mutation_is_detected(self):
        self.native_mutation('W8(0x04000063, 8);','W16(0x04000063, 8);','Dbaa_CgbStop')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_volume_native_balanced_clamp_mutation_is_detected(self):
        self.native_mutation('if (directional && volume > 15)','if ((directional || pan == 255) && volume > 15)','Dbaa_CgbUpdateVolume')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_volume_native_rounding_mutation_is_detected(self):
        self.native_mutation('(sustain * volume + 15) >> 4','(sustain * volume + 14) >> 4','Dbaa_CgbUpdateVolume')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_counter_mutation_is_detected(self):
        self.native_mutation('tick ? tick - 1u : 14','tick ? tick - 1u : 13','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_status_mask_mutation_is_detected(self):
        self.native_mutation('status & 0xC7','status & 0xC3','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_signed_echo_mutation_is_detected(self):
        self.native_mutation('s8(value) > 0','value > 0','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_wave_copy_extent_mutation_is_detected(self):
        self.native_mutation('offset < 16; offset += 4','offset < 12; offset += 4','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_bias_rounding_mutation_is_detected(self):
        self.native_mutation('(frequency + 2u) & 0x7FCu','(frequency + 1u) & 0x7FCu','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_second_trigger_omission_is_detected(self):
        self.native_mutation('if (number == 1 && !(R8(reg0) & 8))','if (number == 1 && (R8(reg0) & 8))','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_flag_clear_omission_is_detected(self):
        self.native_mutation('W8(channel + 0x1D, 0);','/* missing flag reset */','Dbaa_CgbUpdate')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_update_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_CgbUpdate(host);','return host->call(host->user, target, a0, a1, a2);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_cgb_stop_native_arm_fallback_is_rejected(self):
        self.native_mutation('return Dbaa_CgbStop(host, a0);','return host->call(host->user, target, a0, a1, a2);')


if __name__=='__main__':unittest.main()
