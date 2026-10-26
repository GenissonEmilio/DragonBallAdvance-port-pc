"""Regressions in the consumer used by the native game's audio output."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READY = (ROOT / 'build/native_song_validation/audio_runtime.dll').is_file()


@unittest.skipUnless(READY, 'requires the immutable ROM-validated song corpus')
class GameAudioPcmTests(unittest.TestCase):
    @staticmethod
    def gate(out, source=None):
        command = [sys.executable, 'tools/verify_game_audio_pcm.py', '--quick', '--out-dir', str(out)]
        if source:
            command += ['--source', str(source)]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)

    def test_consumer_matches_original_song_with_rotating_dma_buffers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = self.gate(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((path / 'report.json').read_text())
            self.assertEqual(report['frames'], 80)
            self.assertEqual(report['stereo_samples'], 64291)
            self.assertEqual(len(report['offsets']), 6)
            self.assertTrue(report['pcm16_equal_to_immutable_rom_corpus'])
            self.assertEqual(report['new_arm_cpu_executions'], 0)
            self.assertFalse(report['whole_game_pcm_rom_equal'])

    def mutation(self, before, after):
        source = (ROOT / 'port/windows/game_audio.c').read_text()
        self.assertEqual(source.count(before), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            changed = path / 'mutated.c'
            changed.write_text(source.replace(before, after))
            result = self.gate(path / 'out', changed)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue((path / 'out/failed_case.json').is_file())
            self.assertFalse((path / 'out/report.json').exists())

    def test_exact_timer_boundary_regression_detected(self):
        self.mutation('(elapsed ? elapsed - 1 : 0) / audio.ticks', 'elapsed / audio.ticks')

    def test_dma_rotation_regression_detected(self):
        self.mutation('audio.block_offset = (period - counter) * count;', 'audio.block_offset = 0;')

    def test_stereo_source_regression_detected(self):
        self.mutation('audio.right_base = sound + 0x350;', 'audio.right_base = sound + 0x980;')


if __name__ == '__main__':
    unittest.main()
