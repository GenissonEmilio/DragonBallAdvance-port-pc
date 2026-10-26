"""Complete BENDR image and native bend-range integration tests."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()
TID='music_event_bend_range'


class MusicBendRangeTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_range_complete_image_matches_and_is_excluded_from_c_count(self):
        c={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match_assembly.py','--target',TID,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal']);self.assertFalse(report['counts_as_c']);self.assertNotIn(TID,c)
            self.assertEqual(report['candidate_size'],20);self.assertFalse(report['assembly_postprocessing'])
            self.assertEqual((Path(temp)/(TID+'.bin')).read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10A674:0x10A688])

    def asm_mutation(self,old,new):
        source=(ROOT/'asm'/(TID+'.s')).read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.s';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('match_assembly.py','--target',TID,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_range_field_mutation_fails_byte_gate(self):
        self.asm_mutation('[r1, #0x0F]','[r1, #0x0E]')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_range_flag_mutation_fails_byte_gate(self):
        self.asm_mutation('movs r2, #0x0C','movs r2, #0x08')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_range_arm_c_candidate_fails_complete_byte_gate(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match.py','--target',TID,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((Path(temp)/'report.json').read_text())['equal'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_bend_new_and_existing_notes_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_bend_range.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],2001);self.assertEqual(report['original_instructions_covered'],8)
            self.assertEqual(report['real_player_cases'],624);self.assertEqual(report['real_player_updates'],1248)
            self.assertEqual(report['bend_parameters_tested'],[0,1,63,64,127,128,191,255]);self.assertEqual(report['range_edge_player_cases'],128)
            self.assertEqual(report['parameter_bytes_tested'],256);self.assertEqual(report['status_bytes_tested'],256)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','callback_traces_equal','resource_reads_equal','real_commands_reached_in_every_player_case',
                'unsigned_range_and_bend_preserved_verified','bend_range_flags_verified','neutral_bend_and_zero_range_verified','pitch_compared_to_independent_arithmetic','volume_pan_and_instrument_preserved',
                'note_creation_frequency_verified','existing_note_frequency_update_verified','cgb_pitch_update_flag_verified','frequency_compared_to_independent_rom_call']:
                self.assertTrue(report[key],key)
            self.assertFalse(report['native_new_services_fallback_to_arm']);self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_music_bend_range.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_bend_field_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x0F, range);','W8(track + 0x0E, range);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_bend_flag_mutation_is_detected(self):
        self.native_mutation('W8(track, R8(track) | 0x0Cu);','W8(track, R8(track) | 0x08u);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_existing_flags_preservation_mutation_is_detected(self):
        self.native_mutation('W8(track, R8(track) | 0x0Cu);','W8(track, 0x0Cu);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_parameter_filter_mutation_is_detected(self):
        self.native_mutation('uint32_t range = CALL(0x0810A548, player, track, 0);','uint32_t range = CALL(0x0810AC5C, player, track, 0);')


    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_range_padding_mutation_fails_complete_byte_gate(self):
        self.asm_mutation('.align 2,0\n.size','.align 2,0xFF\n.size')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_signed_range_mutation_is_detected(self):
        self.native_mutation('bend * (int32_t)range',
            'bend * s8(range)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_range_native_parameter_clamp_mutation_is_detected(self):
        self.native_mutation('uint32_t range = CALL(0x0810A548, player, track, 0);',
            'uint32_t value = CALL(0x0810A548, player, track, 0); uint32_t range = value > 127 ? 127 : value;')


if __name__=='__main__':unittest.main()
