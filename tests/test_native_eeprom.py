"""Exercise the real DMA/runtime path; reject wrong capacity, busy and bytes."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / 'build/next/game_timing'
READY = (CURRENT / 'build.json').is_file()


@unittest.skipUnless(READY, 'requires the native game EEPROM integration build')
class NativeEepromTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = CURRENT / 'test_cases'
        cls.parent.mkdir(exist_ok=True)

    @staticmethod
    def gate(directory, stage=None):
        command = [sys.executable, 'tools/verify_native_eeprom_dma.py', '--out-dir', str(directory)]
        command += ['--game-stage', str(stage or CURRENT)]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)

    def test_dma_capacities_erased_busy_and_process_reopen(self):
        with tempfile.TemporaryDirectory(dir=self.parent) as directory:
            path = Path(directory)
            result = self.gate(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((path / 'report.json').read_text())
            self.assertEqual(report['capacities_kbit'], [4, 64])
            self.assertEqual(report['results']['4']['bytes'], 512)
            self.assertEqual(report['results']['64']['bytes'], 8192)
            self.assertTrue(report['busy_ready_bit_verified'])
            self.assertEqual(report['erased_value_verified'], 255)
            self.assertFalse(report['translated_game_functions_executed'])

    def mutation(self, before, after):
        source = (ROOT / 'tools/local/sp00nz_gbarecomp/src/runtime.c').read_text()
        self.assertEqual(source.count(before), 1)
        with tempfile.TemporaryDirectory(dir=self.parent) as directory:
            path = Path(directory)
            changed = path / 'mutated_runtime.c'
            changed.write_text(source.replace(before, after))
            result = subprocess.run([sys.executable, 'tools/build_native_runtime_probe.py',
                                     '--baseline', str(CURRENT / 'build.json'),
                                     '--out-dir', str(path / 'build'), '--runtime-source', str(changed)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = self.gate(path / 'gate', path / 'build')
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('AssertionError', result.stderr)
            self.assertFalse((path / 'gate/report.json').exists())

    def test_four_kbit_address_width_regression_detected(self):
        self.mutation('if (count == 9 || count == 73) eeprom.large = false;',
                      'if (count == 9 || count == 73) eeprom.large = true;')

    def test_sixtyfour_kbit_address_width_regression_detected(self):
        self.mutation('else if (count == 17 || count == 81) eeprom.large = true;',
                      'else if (count == 17 || count == 81) eeprom.large = false;')

    def test_erased_byte_regression_detected(self):
        self.mutation('memset(eeprom.storage, 0xFF, sizeof(eeprom.storage));',
                      'memset(eeprom.storage, 0, sizeof(eeprom.storage));')

    def test_busy_ready_bit_regression_detected(self):
        self.mutation('if (eeprom.busy) {', 'if (false) {')

    def test_persisted_size_regression_detected(self):
        self.mutation('Dbaa_SaveWriteAtomic(eeprom.path, eeprom.storage, eeprom.large ? 8192 : 512)',
                      'Dbaa_SaveWriteAtomic(eeprom.path, eeprom.storage, 8192)')


@unittest.skipUnless(READY, 'requires the native Windows toolchain')
class NativeSaveStorageTests(unittest.TestCase):
    def test_failed_and_interrupted_replacements_preserve_complete_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = subprocess.run([sys.executable, 'tools/verify_save_storage.py', '--out-dir', str(path)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((path / 'report.json').read_text())
            self.assertEqual(report['process_kill_cases'], 12)
            self.assertTrue(report['all_targets_complete'])
            self.assertTrue(report['read_only_failure_preserves_original'])
            self.assertFalse(report['actual_power_loss_tested'])


if __name__ == '__main__':
    unittest.main()
