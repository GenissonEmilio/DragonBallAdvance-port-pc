"""Complete VOICE image, memory ordering and native timbre integration tests."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()
TID='music_event_voice'


class MusicVoiceTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_voice_complete_image_matches_and_is_excluded_from_c_count(self):
        c={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match_assembly.py','--target',TID,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal']);self.assertFalse(report['counts_as_c']);self.assertNotIn(TID,c)
            self.assertEqual(report['candidate_size'],48);self.assertFalse(report['assembly_postprocessing'])
            self.assertEqual((Path(temp)/(TID+'.bin')).read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10A608:0x10A638])

    def asm_mutation(self,old,new):
        source=(ROOT/'asm'/(TID+'.s')).read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.s';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('match_assembly.py','--target',TID,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_voice_assembly_stride_mutation_fails_byte_gate(self):
        self.asm_mutation('lsls r2, r2, #2','lsls r2, r2, #1')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_voice_assembly_destination_mutation_fails_byte_gate(self):
        self.asm_mutation('str r3, [r1, #0x2C]','str r3, [r1, #0x30]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_voice_arm_c_candidate_fails_complete_byte_gate(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match.py','--target',TID,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((Path(temp)/'report.json').read_text())['equal'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_voice_native_timbres_filters_aliases_and_real_player_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_voice.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],1787);self.assertEqual(report['original_instructions_covered'],20)
            self.assertEqual(report['real_player_cases'],320);self.assertEqual(report['real_player_updates'],384)
            self.assertEqual(report['instrument_bytes_tested'],256);self.assertEqual(report['status_bytes_tested'],256)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','callback_traces_equal','resource_reads_equal','real_commands_reached_in_every_player_case',
                'parameter_read_is_raw','filter_uses_record_base_for_all_words','sequential_read_store_aliases_verified',
                'pcm_cgb_wave_adsr_verified','grouped_rhythm_voices_verified','existing_notes_preserved_on_instrument_switch',
                'frequency_compared_to_independent_rom_call']:
                self.assertTrue(report[key],key)
            self.assertFalse(report['native_new_services_fallback_to_arm']);self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_music_voice.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_voice_native_stride_mutation_is_detected(self):
        self.native_mutation('R32(player + 0x30) + 12 * instrument','R32(player + 0x30) + 8 * instrument')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_voice_native_raw_parameter_mutation_is_detected(self):
        self.native_mutation('uint32_t instrument = R8(command);','uint32_t instrument = Dbaa_AudioReadByte(host, command);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_voice_native_filter_base_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x28, Dbaa_AudioFilterAddress(host, source, value));',
            'W32(track + 0x28, Dbaa_AudioFilterAddress(host, source + 4, value));')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_voice_native_sequential_copy_mutation_is_detected(self):
        self.native_mutation('uint32_t value = R32(source);\n  W32(track + 0x24, Dbaa_AudioFilterAddress(host, source, value));\n  value = R32(source + 4);',
            'uint32_t saved = R32(source + 4);\n  uint32_t value = R32(source);\n  W32(track + 0x24, Dbaa_AudioFilterAddress(host, source, value));\n  value = saved;')


if __name__=='__main__':unittest.main()
