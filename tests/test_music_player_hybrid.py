"""Separate exact GBA assembly from behavioral validation of native C."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READY = (ROOT/'baserom.gba').is_file() and (ROOT/'tools/local/gcc-arm-none-eabi-8-2018-q4-major/bin/arm-none-eabi-as.exe').is_file()
NATIVE_READY = READY and importlib.util.find_spec('unicorn') is not None and (ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()

class MusicPlayerHybridTests(unittest.TestCase):
    def run_tool(self, name, *args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_assembly_matches_all_bytes_and_is_not_counted_as_c(self):
        assembly=json.loads((ROOT/'config/assembly.usa.json').read_text())['functions'][0]
        c_ids={t['id'] for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        self.assertNotIn(assembly['id'],c_ids)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'output'
            result=self.run_tool('match_assembly.py','--out-dir',out)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((out/'report.json').read_text())
            self.assertEqual(report['kind'],'assembly')
            self.assertFalse(report['counts_as_c'])
            self.assertTrue(report['equal'])
            self.assertEqual(report['candidate_size'],616)
            self.assertEqual(report['different_bytes'],0)
            self.assertFalse(report['remaining_relocations'])
            self.assertFalse(report['assembly_postprocessing'])
            self.assertEqual((out/'music_player_update.bin').read_bytes(),(ROOT/'baserom.gba').read_bytes()[0x10A724:0x10A98C])

    def assembly_mutation(self, old, new):
        source=(ROOT/'asm/music_player_update.s').read_text()
        self.assertIn(old,source)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'mutated.s';candidate.write_text(source.replace(old,new,1))
            out=Path(temp)/'output'
            result=self.run_tool('match_assembly.py','--source',candidate,'--out-dir',out)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            report=json.loads((out/'report.json').read_text())
            self.assertFalse(report['equal'])
            self.assertGreater(report['different_bytes'],0)

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_assembly_lock_literal_mutation_fails(self):
        self.assembly_mutation('.word 0x68736D53','.word 0x68736D52')

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_assembly_tempo_and_channel_mask_mutations_fail(self):
        for old,new in [('cmp r0, #0x96','cmp r0, #0x95'),('movs r0, #0xc7','movs r0, #0xc3')]:
            with self.subTest(change=new):self.assembly_mutation(old,new)

    @unittest.skipUnless(READY,'requires USA ROM and assembler')
    def test_assembly_extra_allocated_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'extra.s'
            candidate.write_text((ROOT/'asm/music_player_update.s').read_text()+'\n.data\n.word 1\n')
            out=Path(temp)/'output'
            result=self.run_tool('match_assembly.py','--source',candidate,'--out-dir',out)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            self.assertIn('uncompared allocated section',result.stderr)
            self.assertFalse((out/'report.json').exists())

    def test_assembly_wrong_rom_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            rom=Path(temp)/'wrong.gba';rom.write_bytes(bytes(0x200))
            out=Path(temp)/'output'
            result=self.run_tool('match_assembly.py','--rom',rom,'--out-dir',out)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            self.assertIn('exact USA ROM SHA-1',result.stderr)
            self.assertFalse(out.exists())

    @unittest.skipUnless(NATIVE_READY,'requires USA ROM, native compiler and optional Unicorn')
    def test_native_c_matches_original_arm_in_controlled_corpus(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'output'
            result=self.run_tool('verify_music_player.py','--cases',20,'--out-dir',out)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((out/'report.json').read_text())
            self.assertEqual(report['cases'],148)
            self.assertEqual(report['host_pointer_bytes'],8)
            self.assertTrue(report['all_ram_equal'])
            self.assertTrue(report['callback_traces_equal'])
            self.assertEqual(report['command_indices'],list(range(30)))
            self.assertEqual(report['note_indices'],list(range(49)))
            self.assertFalse(report['byte_matching'])
            self.assertFalse(report['full_game_boot'])

    def native_mutation(self, old, new):
        source=(ROOT/'port/audio/music_player_update.c').read_text()
        self.assertEqual(source.count(old),1)
        with tempfile.TemporaryDirectory() as temp:
            candidate=Path(temp)/'mutated.c';candidate.write_text(source.replace(old,new))
            out=Path(temp)/'output'
            result=self.run_tool('verify_music_player.py','--source',candidate,'--cases',20,'--out-dir',out)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertTrue((out/'failed_seed.json').is_file())
            self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires USA ROM, native compiler and optional Unicorn')
    def test_native_clock_mutation_is_detected(self):
        self.native_mutation('R32(player + 12) + 1','R32(player + 12) + 2')

    @unittest.skipUnless(NATIVE_READY,'requires USA ROM, native compiler and optional Unicorn')
    def test_native_stereo_mutation_is_detected(self):
        self.native_mutation('128 + pan','127 + pan')
