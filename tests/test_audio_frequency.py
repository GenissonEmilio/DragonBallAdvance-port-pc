"""Full byte gates and independent ARM/native frequency comparisons."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READY = (ROOT/'baserom.gba').is_file() and (ROOT/'tools/local/agbcc/gcc/agbcc.exe').is_file()
NATIVE_READY = READY and importlib.util.find_spec('unicorn') is not None and (ROOT/'tools/local/w64devkit/bin/gcc.exe').is_file()


class AudioFrequencyTests(unittest.TestCase):
    def run_tool(self, name, *args):
        return subprocess.run([sys.executable, str(ROOT/'tools'/name), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True)

    def c_mutation(self, old, new):
        source = (ROOT/'src/music_calculate_frequency.c').read_text()
        self.assertEqual(source.count(old), 1)
        with tempfile.TemporaryDirectory() as temp:
            source_file = Path(temp)/'changed.c'
            source_file.write_text(source.replace(old, new))
            out = Path(temp)/'out'
            result = self.run_tool('match.py', '--target', 'music_calculate_frequency',
                                   '--source', source_file, '--out-dir', out)
            self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
            report = json.loads((out/'report.json').read_text())
            self.assertFalse(report['equal'])
            self.assertFalse(report['assembly_postprocessing'])

    @unittest.skipUnless(READY, 'requires USA ROM and compiler')
    def test_pcm_clamp_mutation_fails_byte_gate(self):
        self.c_mutation('if (key > 178)', 'if (key > 177)')

    @unittest.skipUnless(READY, 'requires USA ROM and compiler')
    def test_pcm_fine_shift_mutation_fails_byte_gate(self):
        self.c_mutation('(DbaaU32)fine << 24', '(DbaaU32)fine << 23')

    @unittest.skipUnless(NATIVE_READY, 'requires native compiler, Unicorn and ROM')
    def test_native_frequency_results_reads_and_dispatch_match_original(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_tool('verify_audio_frequency.py', '--quick', '--out-dir', temp)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            report = json.loads((Path(temp)/'report.json').read_text())
            self.assertEqual(report['cases'], 40960)
            self.assertEqual(report['channel_bytes_tested'], 256)
            self.assertTrue(report['all_results_equal'])
            self.assertTrue(report['source_reads_equal'])
            self.assertTrue(report['game_ram_unchanged'])
            self.assertTrue(report['callee_saved_registers_preserved'])
            self.assertEqual(report['native_frequency_targets'], [0x0810AC90, 0x0810B78C])
            self.assertEqual(report['arm_fallback_targets'], [])
            self.assertFalse(report['byte_matching'])
            self.assertFalse(report['full_game_boot'])

    def native_mutation(self, old, new):
        source = (ROOT/'port/audio/audio_helpers.c').read_text()
        self.assertEqual(source.count(old), 1)
        with tempfile.TemporaryDirectory() as temp:
            source_file = Path(temp)/'changed.c'
            source_file.write_text(source.replace(old, new))
            out = Path(temp)/'out'
            result = self.run_tool('verify_audio_frequency.py', '--quick', '--helpers-source',
                                   source_file, '--out-dir', out)
            self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
            self.assertTrue((out/'failed_case.json').exists())
            self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(NATIVE_READY, 'requires native compiler, Unicorn and ROM')
    def test_native_pcm_high_word_mutation_is_detected(self):
        self.native_mutation('(uint64_t)frequency * (first + adjustment) >> 32',
                             '(uint64_t)frequency * (first + adjustment) >> 31')

    @unittest.skipUnless(NATIVE_READY, 'requires native compiler, Unicorn and ROM')
    def test_native_pcm_clamp_mutation_is_detected(self):
        self.native_mutation('if (key > 178)', 'if (key > 177)')

    @unittest.skipUnless(NATIVE_READY, 'requires native compiler, Unicorn and ROM')
    def test_native_cgb_signed_rounding_mutation_is_detected(self):
        self.native_mutation('-((-period + divisor - 1) / divisor)', '-((-period) / divisor)')

    @unittest.skipUnless(NATIVE_READY, 'requires native compiler, Unicorn and ROM')
    def test_native_noise_limit_mutation_is_detected(self):
        self.native_mutation('key = 59;', 'key = 58;')

    @unittest.skipUnless(NATIVE_READY, 'requires native compiler, Unicorn and ROM')
    def test_frequency_fallback_to_arm_is_rejected(self):
        self.native_mutation('return Dbaa_MusicCalculateFrequency(host, a0, a1, a2);',
                             'return host->call(host->user, target, a0, a1, a2);')


if __name__ == '__main__':
    unittest.main()
