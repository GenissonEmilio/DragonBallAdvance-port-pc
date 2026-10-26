"""Note creation, channel arbitration and real native dispatch against the ROM."""
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


class SoundUpdateTrackTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_full_assembly_is_exact_and_separate_from_c(self):
        c_ids={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        self.assertNotIn('sound_update_track',c_ids)
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_tool('match_assembly.py','--target','sound_update_track','--out-dir',temp)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertTrue(report['equal'])
            self.assertFalse(report['counts_as_c'])
            self.assertEqual(report['candidate_size'],512)
            self.assertEqual((Path(temp)/'sound_update_track.bin').read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10AA00:0x10AC00])

    def asm_mutation(self,old,new):
        source=(ROOT/'asm/sound_update_track.s').read_text()
        self.assertIn(old,source)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'changed.s';candidate.write_text(source.replace(old,new,1))
            result=self.run_tool('match_assembly.py','--target','sound_update_track','--source',candidate,'--out-dir',Path(temp)/'out')
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertFalse(json.loads((Path(temp)/'out/report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_channel_mask_mutation_fails_exact_gate(self):
        self.asm_mutation('movs r0, #0xc7','movs r0, #0xc3')

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_cgb_sweep_mutation_fails_exact_gate(self):
        self.asm_mutation('movs r1, #8','movs r1, #9')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_arm_c_candidate_is_excluded_and_fails_byte_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_tool('match.py','--target','sound_update_track','--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertFalse(report['equal'])
            self.assertFalse(report['assembly_postprocessing'])

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_clear_modulation_flag_mutation_fails_c_gate(self):
        source=(ROOT/'src/music_clear_modulation.c').read_text()
        self.assertIn('flags = 12;',source)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'changed.c';candidate.write_text(source.replace('flags = 12;','flags = 8;'))
            result=self.run_tool('match.py','--target','music_clear_modulation','--source',candidate,'--out-dir',Path(temp)/'out')
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_notes_and_real_player_dispatch_match_original(self):
        with tempfile.TemporaryDirectory() as temp:
            result=self.run_tool('verify_sound_update_track.py','--cases',16,'--out-dir',temp)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],304)
            self.assertEqual(report['routes'],{'note':144,'player_note':128,'clear_modulation':32})
            self.assertEqual(report['parser_parameter_counts'],[0,1,2,3])
            self.assertEqual(report['original_instructions_covered'],245)
            self.assertTrue(report['all_ram_equal'])
            self.assertTrue(report['callback_traces_equal'])
            self.assertTrue(report['resource_reads_equal'])
            self.assertEqual(len(report['native_audio_targets']),66)
            self.assertFalse(set(report['native_audio_targets'])&set(report['arm_fallback_targets']))
            self.assertFalse(report['byte_matching'])
            self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        source=(ROOT/'port/audio/audio_helpers.c').read_text()
        self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'changed.c';candidate.write_text(source.replace(old,new))
            out=Path(temp)/'out'
            result=self.run_tool('verify_sound_update_track.py','--cases',16,'--helpers-source',candidate,'--out-dir',out)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertTrue((out/'failed_case.json').exists())
            self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_optional_key_mutation_is_detected(self):
        self.native_mutation('W8(track + 5, value);','W8(track + 5, value + 1);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_owner_tie_mutation_is_detected(self):
        self.native_mutation('if (owner >= best_track)','if (owner > best_track)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_releasing_channel_mutation_is_detected(self):
        self.native_mutation('if (status & 0x40) {','if (status & 0x20) {')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_frequency_callback_substitution_is_detected(self):
        self.native_mutation('CALL(R32(sound + 0x30), cgb,','CALL(0x0810B78D, cgb,')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_modulation_flags_mutation_is_detected(self):
        self.native_mutation('uint32_t flags = R8(track + 0x18) ? 3 : 12;','uint32_t flags = R8(track + 0x18) ? 3 : 8;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_zero_channel_count_entry_is_preserved(self):
        self.native_mutation('channel = sound + 0x50;','if (count == 0) return 0;\n    channel = sound + 0x50;')


if __name__=='__main__':
    unittest.main()
