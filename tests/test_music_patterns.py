"""Complete-byte gates and native pattern call/return/repeat regression checks."""
from pathlib import Path
import importlib.util, json, subprocess, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class MusicPatternTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_four_complete_images_match_and_c_assembly_counts_stay_separate(self):
        c_ids={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        rom=(ROOT/'baserom.gba').read_bytes();total=0
        for tid,addr,size,tool in [('music_event_pattern',0x10A574,28,'match_assembly.py'),
            ('music_event_pattern_end',0x10A590,20,'match.py'),('music_event_repeat',0x10A5A4,48,'match_assembly.py'),
            ('music_read_command_filtered',0x10A548,12,'match_assembly.py')]:
            with self.subTest(target=tid),tempfile.TemporaryDirectory()as temp:
                out=Path(temp);r=self.run_tool(tool,'--target',tid,'--out-dir',out)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                report=json.loads((out/'report.json').read_text());self.assertTrue(report['equal'])
                self.assertFalse(report['assembly_postprocessing']);self.assertEqual(report['candidate_size'],size)
                self.assertEqual((out/(tid+'.bin')).read_bytes(),rom[addr:addr+size]);total+=size
                self.assertEqual(tid in c_ids,tool=='match.py')
                if tool=='match_assembly.py':self.assertFalse(report['counts_as_c'])
        self.assertEqual(total,108)

    def mutation(self,tool,tid,source,old,new):
        text=(ROOT/source).read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            changed=Path(temp)/Path(source).name;changed.write_text(text.replace(old,new))
            out=Path(temp)/'out';r=self.run_tool(tool,'--target',tid,'--source',changed,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_pattern_end_stack_stride_mutation_fails_c_gate(self):
        self.mutation('match.py','music_event_pattern_end','src/music_event_pattern_end.c','depth <<= 2;','depth <<= 1;')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_pattern_limit_mutation_fails_assembly_gate(self):
        self.mutation('match_assembly.py','music_event_pattern','asm/music_event_pattern.s','cmp r2, #3','cmp r2, #4')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_repeat_exit_stride_mutation_fails_assembly_gate(self):
        self.mutation('match_assembly.py','music_event_repeat','asm/music_event_repeat.s','adds r2, #5','adds r2, #4')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_reader_filter_mutation_fails_assembly_gate(self):
        self.mutation('match_assembly.py','music_read_command_filtered','asm/music_read_command_filtered.s','b Sound_FilterAddress','bx lr')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_three_arm_c_candidates_differ_and_remain_excluded(self):
        for tid in ['music_event_pattern','music_event_repeat','music_read_command_filtered']:
            with self.subTest(target=tid),tempfile.TemporaryDirectory()as temp:
                r=self.run_tool('match.py','--target',tid,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
                self.assertEqual(r.returncode,1,r.stdout+r.stderr)
                self.assertFalse(json.loads((Path(temp)/'report.json').read_text())['equal'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_patterns_returns_repeats_reader_and_real_player_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_patterns.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],3560);self.assertEqual(report['original_instructions_covered'],50)
            self.assertEqual(len(report['native_audio_targets']),66);self.assertEqual(report['real_player_cases'],384)
            self.assertEqual(report['nested_pattern_levels'],[1,2,3]);self.assertEqual(report['arm_fallback_targets'],[])
            for key in ['depth_bytes_tested','repeat_bytes_tested','count_bytes_tested']:self.assertEqual(report[key],256)
            for key in ['all_ram_equal','callback_traces_equal','resource_reads_equal','reader_results_equal',
                'real_commands_reached_in_every_player_case','return_cursors_verified','overflow_track_end_verified','held_notes_verified']:
                self.assertTrue(report[key],key)
            self.assertFalse(report['native_new_services_fallback_to_arm']);self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        text=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            source=Path(temp)/'changed.c';source.write_text(text.replace(old,new))
            out=Path(temp)/'out';r=self.run_tool('verify_music_patterns.py','--cases',0,'--helpers-source',source,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_pattern_depth_limit_mutation_is_detected(self):
        self.native_mutation('if (depth >= 3)','if (depth >= 4)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_pattern_stack_stride_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x44 + depth * 4, command + 4);','W32(track + 0x44 + depth * 8, command + 4);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_pattern_return_index_mutation_is_detected(self):
        self.native_mutation('R32(track + 0x44 + depth * 4)','R32(track + 0x48 + depth * 4)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_repeat_counter_wrap_mutation_is_detected(self):
        self.native_mutation('uint32_t repeat = R8(track + 3) + 1;','uint32_t repeat = (R8(track + 3) + 1) & 255;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_reader_alias_order_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x40, command + 1);\n  return Dbaa_AudioReadByte(host, command);',
            'uint32_t byte = Dbaa_AudioReadByte(host, command);\n  W32(track + 0x40, command + 1);\n  return byte;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_repeat_exit_cursor_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x40, command + 5);','W32(track + 0x40, command + 4);')


if __name__=='__main__':unittest.main()
