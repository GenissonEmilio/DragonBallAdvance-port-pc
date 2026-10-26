"""Byte gates and real native/ARM differential checks for audio services."""
from pathlib import Path
import importlib.util,json,subprocess,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file() and (ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn') is not None and (ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()

class AudioHelperTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    def c_mutation(self,tid,old,new):
        manifest=json.loads((ROOT/'config/functions.usa.json').read_text())
        target=next(t for t in manifest['functions']if t['id']==tid)
        source=(ROOT/target['source']).read_text();self.assertIn(old,source)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'mutated.c';candidate.write_text(source.replace(old,new,1))
            out=Path(temp)/'out';r=self.run_tool('match.py','--target',tid,'--source',candidate,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires USA ROM and compilers')
    def test_unlink_previous_offset_mutation_fails_complete_c_gate(self):
        self.c_mutation('audio_unlink_channel','previous->next = next;','previous->track = (void *)next;')

    @unittest.skipUnless(READY,'requires USA ROM and compilers')
    def test_fine_channel_mask_mutation_fails_complete_c_gate(self):
        self.c_mutation('music_event_fine','0xC7','0xC3')

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_all_assembly_targets_match_and_remain_separate_from_c(self):
        manifest=json.loads((ROOT/'config/assembly.usa.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            r=self.run_tool('match_assembly.py','--all','--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            rows=json.loads((Path(temp)/'summary.json').read_text())
            self.assertEqual({r['id']for r in rows},{t['id']for t in manifest['functions']})
            self.assertEqual(sum(r['report']['candidate_size']for r in rows),2720)
            for row in rows:
                self.assertTrue(row['report']['equal'])
                self.assertEqual(row['report']['kind'],'assembly')
                self.assertFalse(row['report']['counts_as_c'])

    def asm_mutation(self,tid,old,new):
        manifest=json.loads((ROOT/'config/assembly.usa.json').read_text())
        target=next(t for t in manifest['functions']if t['id']==tid)
        source=(ROOT/target['source']).read_text();self.assertIn(old,source)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'mutated.s';candidate.write_text(source.replace(old,new,1))
            out=Path(temp)/'out';r=self.run_tool('match_assembly.py','--target',tid,'--source',candidate,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_copy_count_mutation_fails_assembly_gate(self):
        self.asm_mutation('sound_copy_command_table','movs r1, #36','movs r1, #35')

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_address_shift_mutation_fails_assembly_gate(self):
        self.asm_mutation('sound_copy_command_table','lsrs r0, r2, #25','lsrs r0, r2, #24')

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_clear_register_list_mutation_fails_assembly_gate(self):
        self.asm_mutation('audio_clear64','stmia r0!, {r1,r2,r3,r4}','stmia r0!, {r1,r2,r3}')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_audio_corpus_matches_original_and_uses_native_bindings(self):
        with tempfile.TemporaryDirectory() as temp:
            r=self.run_tool('verify_audio_helpers.py','--cases',12,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],144)
            self.assertEqual(len(report['routes']),12)
            self.assertTrue(report['all_ram_equal'])
            self.assertTrue(report['callback_traces_equal'])
            self.assertTrue(report['meaningful_return_values_equal'])
            self.assertEqual(len(report['native_audio_targets']),66)
            self.assertFalse(set(report['native_audio_targets']) & set(report['arm_fallback_targets']))
            self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'changed.c';candidate.write_text(source.replace(old,new))
            out=Path(temp)/'out';r=self.run_tool('verify_audio_helpers.py','--cases',12,'--helpers-source',candidate,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists())
            self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_copy_count_mutation_is_detected(self):
        self.native_mutation('remaining = 36;','remaining = 35;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_unlink_previous_offset_mutation_is_detected(self):
        self.native_mutation('W32(previous + 0x34, next);','W32(previous + 0x30, next);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_fade_step_mutation_is_detected(self):
        self.native_mutation('level = (level - 16u) & 65535;','level = (level - 15u) & 65535;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_clear_callback_override_is_preserved(self):
        self.native_mutation('R32(0x03001CFC)','0x0810A4AD')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_clear_exact_size_mutation_is_detected(self):
        self.native_mutation('offset < 64;','offset < 60;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_read_before_address_filter_is_preserved(self):
        self.native_mutation('uint32_t value = R8(source);',
                             'uint32_t value = source < 0x02000000 ? 0 : R8(source);')
