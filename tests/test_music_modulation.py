"""Complete-byte gates and native LFOS/MOD behavior, including cursor aliasing."""
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


class MusicModulationTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_helper_c_and_both_assembly_commands_match_complete_bytes(self):
        c_ids={t['id']for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        self.assertIn('music_read_command_byte',c_ids)
        rom=(ROOT/'baserom.gba').read_bytes()
        for tid,address,size,tool in [('music_read_command_byte',0x10AC5C,12,'match.py'),
                                     ('music_event_lfo_speed',0x10AC68,20,'match_assembly.py'),
                                     ('music_event_mod_depth',0x10AC7C,20,'match_assembly.py')]:
            with self.subTest(tid=tid),tempfile.TemporaryDirectory() as temp:
                r=self.run_tool(tool,'--target',tid,'--out-dir',temp)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                report=json.loads((Path(temp)/'report.json').read_text())
                self.assertTrue(report['equal']);self.assertEqual(report['candidate_size'],size)
                self.assertEqual((Path(temp)/(tid+'.bin')).read_bytes(),rom[address:address+size])
                if tool=='match_assembly.py':self.assertFalse(report['counts_as_c']);self.assertNotIn(tid,c_ids)

    def mutation(self,tool,tid,source,old,new):
        text=(ROOT/source).read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/Path(source).name;path.write_text(text.replace(old,new))
            out=Path(temp)/'out'
            r=self.run_tool(tool,'--target',tid,'--source',path,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_helper_cursor_stride_mutation_fails_c_gate(self):
        self.mutation('match.py','music_read_command_byte','src/music_read_command_byte.c','command + 1','command + 2')

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_helper_read_offset_mutation_fails_c_gate(self):
        self.mutation('match.py','music_read_command_byte','src/music_read_command_byte.c','value = *command;','value = command[1];')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_lfo_field_mutation_fails_assembly_gate(self):
        self.mutation('match_assembly.py','music_event_lfo_speed','asm/music_event_lfo_speed.s','[r1, #0x19]','[r1, #0x17]')

    @unittest.skipUnless(READY,'requires ROM and assembler')
    def test_modulation_field_mutation_fails_assembly_gate(self):
        self.mutation('match_assembly.py','music_event_mod_depth','asm/music_event_mod_depth.s','[r1, #0x17]','[r1, #0x19]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_arm_c_candidates_fail_and_remain_excluded(self):
        for tid in ['music_event_lfo_speed','music_event_mod_depth']:
            with self.subTest(tid=tid),tempfile.TemporaryDirectory() as temp:
                r=self.run_tool('match.py','--target',tid,'--function-map',ROOT/'config/candidates.usa.json','--out-dir',temp)
                self.assertEqual(r.returncode,1,r.stdout+r.stderr)
                report=json.loads((Path(temp)/'report.json').read_text())
                self.assertFalse(report['equal']);self.assertFalse(report['assembly_postprocessing'])

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_commands_helper_and_real_player_match_rom(self):
        with tempfile.TemporaryDirectory() as temp:
            r=self.run_tool('verify_music_modulation.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],2080)
            self.assertEqual(report['routes'],dict(read_byte=256,lfo_speed=256,mod_depth=256,reset_flags=1024,aliases=144,random=16,player_modulation=128))
            self.assertEqual(report['original_instructions_covered'],32)
            self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['arm_fallback_targets'],[])
            for field in ['all_ram_equal','callback_traces_equal','resource_reads_equal','helper_results_equal','real_commands_reached_in_every_player_case','held_note_release_verified']:
                self.assertTrue(report[field],field)
            self.assertEqual(report['parameter_bytes_tested'],256);self.assertEqual(report['status_bytes_tested'],256)
            self.assertEqual(report['real_player_cases'],128)
            self.assertFalse(report['byte_matching']);self.assertFalse(report['full_game_boot'])

    def native_mutation(self,old,new):
        text=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'changed.c';source.write_text(text.replace(old,new))
            out=Path(temp)/'out'
            r=self.run_tool('verify_music_modulation.py','--cases',16,'--helpers-source',source,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_lfo_field_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x19, speed);','W8(track + 0x1B, speed);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_mod_depth_field_mutation_is_detected(self):
        self.native_mutation('W8(track + 0x17, depth);','W8(track + 0x1B, depth);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_lfo_zero_guard_mutation_is_detected(self):
        self.native_mutation('if (!speed)','if (speed)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_mod_zero_guard_mutation_is_detected(self):
        self.native_mutation('if (!depth)','if (depth)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_cursor_alias_read_order_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x40, command + 1);\n  return R8(command);',
                             'uint32_t byte = R8(command);\n  W32(track + 0x40, command + 1);\n  return byte;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_unsigned_helper_return_mutation_is_detected(self):
        self.native_mutation('return R8(command);','return (uint32_t)s8(R8(command));')


if __name__=='__main__':unittest.main()
