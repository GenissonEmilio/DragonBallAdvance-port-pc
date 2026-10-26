"""Reject IRQ priority, acknowledgement and pointer-context regressions."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READY = ((ROOT / 'baserom.gba').is_file()
         and (ROOT / 'tools/local/w64devkit/bin/gcc.exe').is_file()
         and importlib.util.find_spec('unicorn') is not None)


@unittest.skipUnless(READY, 'requires local ROM, Windows compiler and Unicorn')
class NativeIrqTests(unittest.TestCase):
    def run_gate(self, directory, source=None):
        command = [sys.executable, 'tools/verify_native_irq.py', '--quick',
                   '--out-dir', str(directory)]
        if source:
            command += ['--source', str(source)]
        return subprocess.run(command, cwd=ROOT, capture_output=True,
                              text=True, timeout=60)

    def test_original_arm_priority_registers_flags_and_ordered_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_gate(directory)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(directory) / 'report.json').read_text())
            self.assertEqual(report['cases'], 51)
            self.assertEqual(report['original_irq_instructions'], 49)
            for key in ['rom_register_context_equal', 'ordered_data_bus_equal',
                        'io_equal', 'gamepak_panic_detected']:
                self.assertTrue(report[key], key)
            self.assertFalse(report['byte_matching'])
            self.assertFalse(report['native_arm_execution'])

    def mutation(self, before, after):
        original = (ROOT / 'port/native/irq_dispatch.c').read_text()
        self.assertEqual(original.count(before), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            changed = path / 'mutated.c'
            changed.write_text(original.replace(before, after))
            result = self.run_gate(path / 'out', changed)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue((path / 'out/failed_case.json').is_file())
            self.assertFalse((path / 'out/report.json').exists())

    def test_serial_and_timer3_group_mask_mutation_detected(self):
        self.mutation('{0x00C0, 0x0001', '{0x0040, 0x0001')

    def test_gamepak_loop_mutation_detected(self):
        self.mutation('if (pending & 0x2000u)', 'if (pending & 0x4000u)')

    def test_acknowledgement_mutation_detected(self):
        self.mutation('0x04000202, mask, 2', '0x04000202, pending, 2')

    def test_table_literal_mutation_detected(self):
        self.mutation('copied_code + 0xCC', 'copied_code + 0xC8')

    def test_callback_slot_stride_mutation_detected(self):
        self.mutation('index * 4u', 'index * 2u')


if __name__ == '__main__':
    unittest.main()
