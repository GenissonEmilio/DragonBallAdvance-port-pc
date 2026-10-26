"""Complete PORT image and ordered native I/O command integration."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()
TID='music_event_port'


class MusicPortTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_port_complete_image_matches_and_is_excluded_from_c_count(self):
        c={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match_assembly.py','--target',TID,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal']);self.assertFalse(report['counts_as_c']);self.assertNotIn(TID,c)
            self.assertEqual(report['candidate_size'],24);self.assertFalse(report['assembly_postprocessing'])
            image=(Path(temp)/(TID+'.bin')).read_bytes()
            self.assertEqual(image,(ROOT/'baserom.gba').read_bytes()[0x10A6C0:0x10A6D8])
            self.assertEqual(image[-4:],bytes.fromhex('60000004'))

    def asm_mutation(self,old,new):
        source=(ROOT/'asm'/(TID+'.s')).read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.s';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('match_assembly.py','--target',TID,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_port_literal_mutation_fails_byte_gate(self):
        self.asm_mutation('.word 0x04000060','.word 0x04000061')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_port_store_width_mutation_fails_byte_gate(self):
        self.asm_mutation('strb r3, [r0]','strh r3, [r0]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_port_arm_c_candidate_fails_complete_byte_gate(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('match.py','--target',TID,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertFalse(report['equal']);self.assertEqual(report['candidate_size'],28)
            self.assertEqual(report['different_bytes'],15)

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_bus_and_two_player_updates_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_port.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],2975);self.assertEqual(report['observed_port_writes'],3487)
            self.assertEqual(report['original_instructions_covered'],9)
            self.assertEqual(report['real_player_cases'],512);self.assertEqual(report['real_player_updates'],1024)
            for key in ['selector_bytes_tested','parameter_bytes_tested','status_bytes_tested']:self.assertEqual(report[key],256)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','io_images_equal','ordered_reads_and_writes_equal','callback_traces_equal',
                'real_commands_reached_in_every_player_case','raw_selector_and_filtered_value_verified',
                'interior_reader_entry_verified','cursor_two_byte_advance_and_wrap_verified','cursor_before_value_read_verified',
                'io_byte_width_address_order_and_no_duplicates_verified','register_aliases_and_adjacent_bytes_verified',
                'live_note_software_state_preserved','io_mirror_carried_between_updates']:self.assertTrue(report[key],key)
            for key in ['native_new_services_fallback_to_arm','byte_matching','full_game_boot',
                'hardware_register_side_effects_validated','audible_output_validated']:self.assertFalse(report[key],key)

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/'changed.c';changed.write_text(source.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_music_port.py','--cases',0,'--helpers-source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists(),r.stdout+r.stderr);self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_destination_mutation_is_detected(self):
        self.native_mutation('W8(0x04000060u + port_index, port_value);','W8(0x04000061u + port_index, port_value);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_store_width_mutation_is_detected(self):
        self.native_mutation('W8(0x04000060u + port_index, port_value);','W16(0x04000060u + port_index, port_value);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_cursor_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x40, port_value_source + 1);','W32(track + 0x40, port_value_source);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_value_filter_mutation_is_detected(self):
        self.native_mutation('uint32_t port_value = Dbaa_AudioReadByte(host, port_value_source);','uint32_t port_value = R8(port_value_source);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_raw_selector_mutation_is_detected(self):
        self.native_mutation('uint32_t port_index = R8(port_source);','uint32_t port_index = Dbaa_AudioReadByte(host, port_source);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_duplicate_write_is_detected(self):
        statement='W8(0x04000060u + port_index, port_value);'
        self.native_mutation(statement,statement+'\n  '+statement)

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_port_native_value_read_order_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x40, port_value_source + 1);\n  uint32_t port_value = Dbaa_AudioReadByte(host, port_value_source);',
            'uint32_t port_value = Dbaa_AudioReadByte(host, port_value_source);\n  W32(track + 0x40, port_value_source + 1);')


if __name__=='__main__':unittest.main()
