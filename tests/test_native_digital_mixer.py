"""Use original GBA mixing as the oracle for routing, ratio and DAC clipping."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READY = (ROOT / 'build/next/psg_reference/mgba_build/libmgba.a').is_file()


@unittest.skipUnless(READY, 'requires the pinned local hardware reference')
class NativeDigitalMixerTests(unittest.TestCase):
    @staticmethod
    def gate(out, source=None):
        command = [sys.executable, 'tools/verify_digital_mixer.py', '--quick', '--out-dir', str(out)]
        if source:
            command += ['--source', str(source)]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)

    def test_original_hardware_mix_routes_and_saturation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = self.gate(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((path / 'report.json').read_text())
            self.assertEqual(report['cases'], 4608)
            self.assertEqual(report['original_mgba_mix_calls'], 2304)
            self.assertTrue(report['pcm16_equal_to_original_digital_mix'])
            self.assertGreater(report['dac_clipped_cases'], 0)
            self.assertFalse(report['gba_byte_matching'])

    def mutation(self, before, after):
        source = (ROOT / 'port/audio/digital_mixer.c').read_text()
        self.assertEqual(source.count(before), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            changed = path / 'mutated.c'
            changed.write_text(source.replace(before, after))
            result = self.gate(path / 'out', changed)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue((path / 'out/failed_case.json').is_file())
            self.assertFalse((path / 'out/report.json').exists())

    def test_direct_sound_route_regression_detected(self):
        self.mutation('left += a;', 'left += b;')

    def test_psg_ratio_regression_detected(self):
        self.mutation('int left = (int)psg_left >> (4 - (control & 3));',
                      'int left = (int)psg_left >> (3 - (control & 3));')

    def test_dac_clamp_regression_detected(self):
        self.mutation('if (dac > 1023) {', 'if (dac > 2047) {')


if __name__ == '__main__':
    unittest.main()
