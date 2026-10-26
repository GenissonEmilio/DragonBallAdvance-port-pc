"""Full GBA byte comparison and native held-note termination against the ROM."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file() and (ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn') is not None and (ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class MusicEndTieTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_exact_assembly_remains_separate_from_c(self):
        c_ids={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        self.assertNotIn('music_event_end_tie',c_ids)
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_tool('match_assembly.py','--target','music_event_end_tie','--out-dir',temp)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal']);self.assertFalse(report['counts_as_c'])
            self.assertEqual(report['candidate_size'],64)
            self.assertEqual((Path(temp)/'music_event_end_tie.bin').read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10AC00:0x10AC40])

    def asm_mutation(self,old,new):
        source=(ROOT/'asm/music_event_end_tie.s').read_text();self.assertIn(old,source)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'changed.s';candidate.write_text(source.replace(old,new,1))
            out=Path(temp)/'out'
            result=self.run_tool('match_assembly.py','--target','music_event_end_tie','--source',candidate,'--out-dir',out)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_status_mask_mutation_fails_full_byte_gate(self):
        self.asm_mutation('movs r4, #0x83','movs r4, #0x87')

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_key_field_mutation_fails_full_byte_gate(self):
        self.asm_mutation('ldrb r0, [r1, #0x11]','ldrb r0, [r1, #8]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_arm_c_candidate_fails_and_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_tool('match.py','--target','music_event_end_tie','--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertFalse(report['equal']);self.assertFalse(report['assembly_postprocessing'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_end_tie_and_real_held_note_lifecycle_match_rom(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_tool('verify_music_end_tie.py','--cases',16,'--out-dir',temp)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],976)
            self.assertEqual(report['routes'],dict(status=512,parameter=256,lists=128,random=16,player_held_note=64))
            self.assertEqual(report['original_instructions_covered'],32)
            self.assertTrue(report['all_ram_equal']);self.assertTrue(report['resource_reads_equal'])
            self.assertTrue(report['callback_traces_equal'])
            self.assertEqual(report['status_bytes_tested'],256);self.assertEqual(report['parameter_bytes_tested'],256)
            self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['arm_fallback_targets'],[])
            self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'changed.c';candidate.write_text(source.replace(old,new))
            out=Path(temp)/'out'
            result=self.run_tool('verify_music_end_tie.py','--cases',16,'--helpers-source',candidate,'--out-dir',out)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_status_mask_mutation_is_detected(self):
        self.native_mutation('status & 0x83','status & 0x87')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_pitched_key_field_mutation_is_detected(self):
        self.native_mutation('R8(channel + 0x11) == key','R8(channel + 8) == key')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_parameter_boundary_mutation_is_detected(self):
        self.native_mutation('if (key < 0x80) {','if (key <= 0x80) {')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_first_match_only_mutation_is_detected(self):
        self.native_mutation('W8(channel, status | 0x40);\n      break;','W8(channel, status | 0x40);\n      continue;')


if __name__=='__main__':unittest.main()
