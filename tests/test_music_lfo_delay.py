"""Complete LFODL image and native delay/countdown integration tests."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()
TID='music_event_lfo_delay'


class MusicLfoDelayTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_delay_complete_image_matches_and_is_excluded_from_c_count(self):
        c={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match_assembly.py','--target',TID,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal']);self.assertFalse(report['counts_as_c']);self.assertNotIn(TID,c)
            self.assertEqual(report['candidate_size'],12);self.assertFalse(report['assembly_postprocessing'])
            self.assertEqual((Path(temp)/(TID+'.bin')).read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10A688:0x10A694])

    def asm_mutation(self,old,new):
        source=(ROOT/'asm'/(TID+'.s')).read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.s';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('match_assembly.py','--target',TID,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_delay_field_mutation_fails_byte_gate(self):
        self.asm_mutation('[r1, #0x1B]','[r1, #0x1C]')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_delay_filter_mutation_fails_byte_gate(self):
        self.asm_mutation('bl Music_ReadCommandFiltered','bl Music_ReadCommandByte')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_delay_padding_mutation_fails_complete_byte_gate(self):
        self.asm_mutation('.align 2,0\n.size','.align 2,0xFF\n.size')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_delay_arm_c_candidate_fails_complete_byte_gate(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match.py','--target',TID,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertFalse(report['equal']);self.assertEqual(report['candidate_size'],12);self.assertEqual(report['different_bytes'],5)

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_note_start_and_live_timing_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_lfo_delay.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],1901);self.assertEqual(report['original_instructions_covered'],4)
            self.assertEqual(report['real_player_cases'],512);self.assertEqual(report['real_player_updates'],1792)
            self.assertEqual(report['real_player_ticks'],33923)
            self.assertEqual(report['parameter_bytes_tested'],256);self.assertEqual(report['status_bytes_tested'],256)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','callback_traces_equal','resource_reads_equal','real_commands_reached_in_every_player_case',
                'unsigned_preset_verified','live_counter_phase_and_flags_preserved','note_start_load_and_reset_verified',
                'zero_delay_preserves_note_start_phase','countdown_and_first_modulation_tick_verified','maximum_255_delay_verified',
                'pitch_compared_to_independent_arithmetic','instrument_and_note_key_preserved','pcm_cgb_and_pitch_volume_modulation_verified',
                'frequency_compared_to_independent_rom_call','cgb_modulation_flags_verified']:
                self.assertTrue(report[key],key)
            self.assertFalse(report['native_new_services_fallback_to_arm']);self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_music_lfo_delay.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_field_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x1B, lfo_delay);','W8(track + 0x1C, lfo_delay);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_counter_reset_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x1B, lfo_delay);','W8(track + 0x1B, lfo_delay); W8(track + 0x1C, lfo_delay);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_phase_reset_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x1B, lfo_delay);','W8(track + 0x1B, lfo_delay); W8(track + 0x1A, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_extra_flags_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x1B, lfo_delay);','W8(track + 0x1B, lfo_delay); W8(track, R8(track) | 12u);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_parameter_filter_mutation_is_detected(self):
        self.native_mutation('uint32_t lfo_delay = CALL(0x0810A548, player, track, 0);','uint32_t lfo_delay = CALL(0x0810AC5C, player, track, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_delay_native_parameter_clamp_mutation_is_detected(self):
        self.native_mutation('uint32_t lfo_delay = CALL(0x0810A548, player, track, 0);',
            'uint32_t value = CALL(0x0810A548, player, track, 0); uint32_t lfo_delay = value > 127 ? 127 : value;')


if __name__=='__main__':unittest.main()
