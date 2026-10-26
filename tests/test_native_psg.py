"""Independent GBA I/O/scheduler checks for the standalone native PSG adapter."""
from pathlib import Path
import ctypes
import _ctypes
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
READY = ((ROOT / 'tools/local/w64devkit/bin/gcc.exe').is_file() and
         (ROOT / 'build/next/psg_reference/mgba_build/libmgba.a').is_file())


@unittest.skipUnless(READY, 'requires the pinned local PSG hardware reference')
class NativePsgTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name)
        cls.result = cls.run_gate(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @staticmethod
    def run_gate(out, source=None):
        command = [sys.executable, 'tools/verify_native_psg.py', '--quick',
                   '--out-dir', str(out)]
        if source:
            command += ['--source', str(source)]
        return subprocess.run(command, cwd=ROOT, capture_output=True,
                              text=True, timeout=120)

    def test_original_hardware_scheduler_channels_wave_banks_and_io_widths(self):
        result = self.result
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((self.path / 'report.json').read_text())
        self.assertEqual(report['stereo_samples'], 20000)
        self.assertEqual(report['writes'], 258)
        self.assertTrue(report['raw_digital_psg_equal'])
        self.assertTrue(report['nr52_equal'])
        self.assertEqual(report['soundbias_resolutions_tested'], [0, 1, 2, 3])
        self.assertTrue(report['dynamic_soundbias_io_tested'])
        for key in ['cpu_execution', 'native_cpu_core_linked',
                    'gba_byte_matching', 'analog_output_bit_exact',
                    'rom_pcm_validation']:
            self.assertFalse(report[key], key)

    def test_unsupported_bus_access_and_reversed_time_are_rejected(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        library = ctypes.CDLL(str(self.path / 'psg.dll'))
        library.Dbaa_PsgCreate.restype = ctypes.c_void_p
        library.Dbaa_PsgDestroy.argtypes = [ctypes.c_void_p]
        library.Dbaa_PsgAdvance.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        library.Dbaa_PsgWrite.argtypes = [ctypes.c_void_p, ctypes.c_uint64,
                                         ctypes.c_uint32, ctypes.c_uint32,
                                         ctypes.c_uint]
        state = library.Dbaa_PsgCreate()
        self.assertTrue(state)
        try:
            self.assertEqual(library.Dbaa_PsgAdvance(state, 1024), 1)
            self.assertEqual(library.Dbaa_PsgAdvance(state, 1023), 0)
            for address, width in [(0x0400005F, 1), (0x040000A0, 1),
                                    (0xFFFFFFFF, 4), (0x04000060, 3),
                                    (0x04000061, 2)]:
                self.assertEqual(library.Dbaa_PsgWrite(state, 1024, address,
                                                       0xFFFFFFFF, width), 0)
        finally:
            library.Dbaa_PsgDestroy(state)
            _ctypes.FreeLibrary(library._handle)

    def mutation(self, before, after):
        source = (ROOT / 'port/audio/psg_mgba.c').read_text()
        self.assertEqual(source.count(before), 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            changed = path / 'mutated.c'
            changed.write_text(source.replace(before, after))
            result = self.run_gate(path / 'out', changed)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue((path / 'out/failed_case.json').is_file())
            self.assertFalse((path / 'out/report.json').exists())

    def test_wave_bank_regression_detected(self):
        self.mutation('unsigned bank = p->chip.enable ? !p->chip.ch3.bank : 1;',
                      'unsigned bank = p->chip.enable ? p->chip.ch3.bank : 1;')

    def test_frame_sequencer_frequency_regression_detected(self):
        self.mutation('p->frame_cycle += 32768;', 'p->frame_cycle += 65536;')

    def test_soundbias_resolution_regression_detected(self):
        self.mutation('p->sample_interval = 0x200u >> resolution;',
                      'p->sample_interval = 512;')

    def test_stereo_routing_regression_detected(self):
        self.mutation('case 0x81:\n    GBAudioWriteNR51(c, v);',
                      'case 0x81:\n    GBAudioWriteNR50(c, v);')


if __name__ == '__main__':
    unittest.main()
