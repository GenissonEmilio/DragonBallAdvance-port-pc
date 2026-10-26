"""Exact C images and native MEMACC/XCMD behavior against the USA ROM."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
READY=(ROOT/'baserom.gba').is_file()and(ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY=READY and importlib.util.find_spec('unicorn')is not None and(ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()
IDS=['music_event_memory','music_event_extended','music_event_extended_end','music_event_wave',
     'music_event_type','music_event_attack','music_event_decay','music_event_sustain','music_event_release',
     'music_event_echo_volume','music_event_echo_length','music_event_length','music_event_sweep','music_event_goto']


class MusicMemoryTests(unittest.TestCase):
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    @unittest.skipUnless(READY,'requires ROM and toolchain')
    def test_all_fourteen_c_images_match_every_byte(self):
        targets={t['id']:t for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']}
        rom=(ROOT/'baserom.gba').read_bytes();total=0
        with tempfile.TemporaryDirectory()as temp:
            for tid in IDS:
                with self.subTest(target=tid):
                    out=Path(temp)/tid;r=self.run_tool('match.py','--target',tid,'--out-dir',out)
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                    report=json.loads((out/'report.json').read_text());t=targets[tid];size=t['size']
                    self.assertTrue(report['equal']);self.assertFalse(report['assembly_postprocessing'])
                    self.assertEqual(report['candidate_size'],size)
                    offset=int(t['address'],0)-0x08000000
                    self.assertEqual((out/(tid+'.bin')).read_bytes(),rom[offset:offset+size]);total+=size
        self.assertEqual(total,664)

    def c_mutation(self,tid,old,new):
        t=next(t for t in json.loads((ROOT/'config/functions.usa.json').read_text())['functions']if t['id']==tid)
        text=(ROOT/t['source']).read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            source=Path(temp)/'changed.c';source.write_text(text.replace(old,new))
            out=Path(temp)/'out';r=self.run_tool('match.py','--target',tid,'--source',source,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertFalse(json.loads((out/'report.json').read_text())['equal'])

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_memory_comparison_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_memory','MEMACC_COND_JUMP(left < right)','MEMACC_COND_JUMP(left <= right)')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_memory_arithmetic_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_memory','result = left - data;','result = left + data;')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_memory_callback_slot_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_memory','gSoundCommands[1]','gSoundCommands[0]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_extended_dispatch_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_extended','gMusicExtendedCommands[n]','gMusicExtendedCommands[0]')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_wave_byte_offset_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_wave','byte = command[1];','byte = command[2];')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_type_field_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_type','destination = track + 0x24;','destination = track + 0x25;')

    @unittest.skipUnless(READY,'requires ROM and compiler')
    def test_goto_byte_offset_mutation_fails_complete_byte_gate(self):
        self.c_mutation('music_event_goto','value = command[3];','value = command[2];')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_memory_extended_and_real_player_match_rom(self):
        with tempfile.TemporaryDirectory()as temp:
            r=self.run_tool('verify_music_memory.py','--cases',16,'--out-dir',temp)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            report=json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'],1546)
            self.assertEqual(report['original_instructions_covered'],264)
            self.assertEqual(report['operation_bytes_tested'],256);self.assertEqual(report['extended_indices_tested'],list(range(12)))
            self.assertEqual(len(report['native_audio_targets']),66)
            self.assertEqual(report['real_player_cases'],128)
            self.assertEqual(report['arm_fallback_targets'],[0x08010104])
            self.assertTrue(report['all_ram_equal']);self.assertTrue(report['callback_traces_equal']);self.assertTrue(report['resource_reads_equal'])
            self.assertTrue(report['real_commands_reached']);self.assertTrue(report['real_conditional_branches_verified']);self.assertTrue(report['held_notes_verified'])
            self.assertFalse(report['native_new_services_fallback_to_arm']);self.assertFalse(report['full_game_boot']);self.assertFalse(report['byte_matching'])

    def native_mutation(self,old,new):
        text=(ROOT/'port/audio/audio_helpers.c').read_text();self.assertEqual(text.count(old),1)
        with tempfile.TemporaryDirectory()as temp:
            source=Path(temp)/'changed.c';source.write_text(text.replace(old,new))
            out=Path(temp)/'out';r=self.run_tool('verify_music_memory.py','--cases',0,'--helpers-source',source,'--out-dir',out)
            self.assertEqual(r.returncode,1,r.stdout+r.stderr)
            self.assertTrue((out/'failed_case.json').exists());self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_memory_comparison_mutation_is_detected(self):
        self.native_mutation('taken = left > right;','taken = left >= right;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_memory_arithmetic_mutation_is_detected(self):
        self.native_mutation('W8(address, R8(address) - data);','W8(address, R8(address) + data);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_skipped_pointer_size_mutation_is_detected(self):
        self.native_mutation('W32(track + 0x40, R32(track + 0x40) + 4);','W32(track + 0x40, R32(track + 0x40) + 3);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_dynamic_jump_callback_mutation_is_detected(self):
        self.native_mutation('CALL(R32(0x03001C74), player, track, 0);','CALL(0x0810A555, player, track, 0);')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_extended_stride_mutation_is_detected(self):
        self.native_mutation('R32(0x08A67708 + index * 4)','R32(0x08A67708 + index * 8)')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_wave_byte_order_mutation_is_detected(self):
        self.native_mutation('wave |= R8(command + 2) << 16;','wave |= R8(command + 2) << 8;')

    @unittest.skipUnless(NATIVE_READY,'requires native compiler, Unicorn and ROM')
    def test_native_goto_low_byte_filter_mutation_is_detected(self):
        self.native_mutation('destination |= Dbaa_AudioReadByte(host, command);','destination |= R8(command);')


if __name__=='__main__':unittest.main()
