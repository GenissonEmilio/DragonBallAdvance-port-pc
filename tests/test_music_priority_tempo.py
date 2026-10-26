"""Exact GBA images and native priority/tempo behavior, with negative controls."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class MusicPriorityTempoTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_both_complete_images_match_and_remain_excluded_from_c_counts(self):
        c={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        rom=(ROOT/'baserom.gba').read_bytes();total=0
        for tid,offset,size in [('music_event_priority',0x10A5D4,12),('music_event_tempo',0x10A5E0,20)]:
            with self.subTest(target=tid),tempfile.TemporaryDirectory()as temp:
                r=self.run_tool('match_assembly.py','--target',tid,'--out-dir',temp)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                report=json.loads((Path(temp)/'report.json').read_text())
                self.assertTrue(report['equal']);self.assertFalse(report['counts_as_c']);self.assertNotIn(tid,c)
                self.assertFalse(report['assembly_postprocessing']);self.assertEqual(report['candidate_size'],size)
                self.assertEqual((Path(temp)/(tid+'.bin')).read_bytes(),rom[offset:offset+size]);total+=size
        self.assertEqual(total,32)

    def mutation(self,tid,old,new):
        path=ROOT/'asm'/(tid+'.s');s=path.read_text();self.assertEqual(s.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/path.name;changed.write_text(s.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('match_assembly.py','--target',tid,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_priority_field_mutation_fails_byte_gate(self):
        self.mutation('music_event_priority','[r1, #0x1D]','[r1, #0x1C]')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_tempo_multiplier_mutation_fails_byte_gate(self):
        self.mutation('music_event_tempo','lsls r3, #1','lsls r3, #2')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_tempo_scale_offset_mutation_fails_byte_gate(self):
        self.mutation('music_event_tempo','[r0, #0x1E]','[r0, #0x1C]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_arm_c_candidates_differ_and_remain_excluded(self):
        for tid in ['music_event_priority','music_event_tempo']:
            with self.subTest(target=tid),tempfile.TemporaryDirectory()as temp:
                r=self.run_tool('match.py','--target',tid,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
                self.assertEqual(r.returncode,1,r.stdout+r.stderr)
                self.assertFalse(json.loads((Path(temp)/'report.json').read_text())['equal'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_commands_and_two_player_updates_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_priority_tempo.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],3029);self.assertEqual(report['original_instructions_covered'],13)
            self.assertEqual(report['real_player_cases'],128);self.assertEqual(report['real_player_updates'],256)
            self.assertEqual(report['parameter_bytes_tested'],256);self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['all_ram_equal','callback_traces_equal','resource_reads_equal','real_commands_reached_in_every_player_case',
                'note_priority_verified','tempo_interval_unsigned_product_verified','next_update_tempo_effect_verified']:
                self.assertTrue(report[key],key)
            self.assertFalse(report['native_new_services_fallback_to_arm']);self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        text=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            source=Path(temp)/'changed.c';source.write_text(text.replace(old,new));out=Path(temp)/'out'
            r=self.run_tool('verify_music_priority_tempo.py','--cases',0,'--helpers-source',source,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_priority_field_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x1D, priority);','W8(track + 0x1B, priority);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_tempo_multiplier_mutation_is_detected(self):
        self.native_mutation('uint32_t tempo = CALL(0x0810A548, player, track, 0) << 1;','uint32_t tempo = CALL(0x0810A548, player, track, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_tempo_product_truncation_mutation_is_detected(self):
        self.native_mutation('(tempo * scale) >> 8','((tempo * scale) & 65535) >> 8')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_tempo_unsigned_scale_mutation_is_detected(self):
        self.native_mutation('uint32_t scale = R16(player + 0x1E);','uint32_t scale = (uint32_t)(int16_t)R16(player + 0x1E);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_tempo_parameter_filter_mutation_is_detected(self):
        self.native_mutation('uint32_t tempo = CALL(0x0810A548, player, track, 0) << 1;','uint32_t tempo = CALL(0x0810AC5C, player, track, 0) << 1;')


if __name__=='__main__':unittest.main()
