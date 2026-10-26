"""Synthetic ARMv4T fixtures only; the game ROM is not required by the tests."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("dbaa", Path(__file__).resolve().parents[1] / "tools/dbaa.py")
dbaa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dbaa)


def synthetic_rom():
    data = bytearray(0x200)
    struct.pack_into("<I", data, 0, 0xEA00002E)  # b 0x080000c0
    data[0xA0:0xAC] = b"TEST FIXTURE"
    data[0xAC:0xB0] = b"BDVE"
    data[0xB2] = 0x96
    data[0xBD] = dbaa.header_checksum(data)
    return bytes(data)


class RomTests(unittest.TestCase):
    def test_header_checksum_and_profile_need_full_hash(self):
        rom = synthetic_rom()
        unknown = dbaa.inspect_rom(rom, [])
        self.assertTrue(unknown["header"]["valid"])
        self.assertIsNone(unknown["known_profile"])
        profile = {"game_code": "BDVE", "sha1": hashlib.sha1(rom).hexdigest()}
        self.assertTrue(dbaa.inspect_rom(rom, [profile])["profile_header_consistent"])
        modified = rom[:-1] + b"\x01"
        self.assertIsNone(dbaa.inspect_rom(modified, [profile])["known_profile"])

    def test_header_corruption(self):
        rom = bytearray(synthetic_rom())
        rom[0xA0] ^= 1
        self.assertFalse(dbaa.inspect_rom(rom, [])["header"]["valid"])
        with self.assertRaises(ValueError):
            dbaa.inspect_rom(bytes(16), [])

    def test_arm_pc_bias_and_negative_displacement(self):
        self.assertEqual(dbaa.reset_branch(synthetic_rom()), 0x080000C0)
        self.assertEqual(dbaa.reset_branch(struct.pack("<I", 0xEAFFFFFE)), dbaa.ROM_BASE)
        self.assertIsNone(dbaa.reset_branch(b"\x00" * 4))

    def test_range_addresses_and_offsets(self):
        rom = synthetic_rom()
        self.assertEqual(dbaa.region(rom, 0xC0, 4), dbaa.region(rom, 0x080000C0, 4))
        for start, size in ((-1, 4), (0, 0), (0x1FF, 2), (0x0A000000, 4), (0, -1)):
            with self.assertRaises(ValueError):
                dbaa.region(rom, start, size)

    def test_driver_marker_is_only_a_lead(self):
        rom = synthetic_rom() + b"EEPROM_V124\0"
        markers = dbaa.inspect_rom(rom, [])["save_driver_markers"]
        self.assertEqual(markers, [{"name": "EEPROM_V124", "offset": "0x00000200"}])


class CompareTests(unittest.TestCase):
    def test_equal_and_differing_sizes(self):
        self.assertTrue(dbaa.compare_bytes(b"\x00\x01", b"\x00\x01")["equal"])
        for candidate in (b"\x00", b"\x00\x01\x00", b"\x00\x02"):
            report = dbaa.compare_bytes(b"\x00\x01", candidate)
            self.assertFalse(report["equal"])
            self.assertEqual(report["different_bytes"], 1)

    def test_difference_count_is_not_truncated_by_preview(self):
        report = dbaa.compare_bytes(bytes(32), bytes([1]) * 32, limit=3)
        self.assertEqual(report["different_bytes"], 32)
        self.assertEqual(len(report["first_differences"]), 3)

    def test_inputs_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rom.gba"
            path.write_bytes(b"original")
            with self.assertRaises(ValueError):
                dbaa.write_file(path, b"wrong", (path,))
            self.assertEqual(path.read_bytes(), b"original")

    def test_cli_failure_codes_and_success(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            first, second = Path(temp) / "a.bin", Path(temp) / "b.bin"
            first.write_bytes(b"a")
            second.write_bytes(b"b")
            self.assertEqual(dbaa.main(["compare", str(first), str(second)]), 1)
            self.assertEqual(dbaa.main(["compare", str(first), str(first)]), 0)
            self.assertEqual(dbaa.main(["inspect", str(first)]), 2)
            first.write_bytes(synthetic_rom())
            self.assertEqual(dbaa.main(["inspect", str(first), "--require-known"]), 2)


class MapTests(unittest.TestCase):
    def mapping(self):
        return {"sha1": hashlib.sha1(synthetic_rom()).hexdigest(), "regions": [
            {"name": "header", "start": "0x08000000", "size": "0xC0", "kind": "data"},
            {"name": "code", "start": "0x080000C0", "size": "0x10", "kind": "arm"},
        ]}

    def test_map_is_bound_to_exact_rom_and_regions_cannot_overlap(self):
        mapping = self.mapping()
        self.assertEqual(len(dbaa.mapped_regions(synthetic_rom(), mapping)), 2)
        with self.assertRaises(ValueError):
            dbaa.mapped_regions(synthetic_rom() + b"modified", mapping)
        mapping["regions"][1]["start"] = "0x080000BC"
        with self.assertRaises(ValueError):
            dbaa.mapped_regions(synthetic_rom(), mapping)

    def test_map_names_cannot_escape_output_directory(self):
        mapping = self.mapping()
        mapping["regions"][0]["name"] = "../outside"
        with self.assertRaises(ValueError):
            dbaa.mapped_regions(synthetic_rom(), mapping)


class DisassemblyTests(unittest.TestCase):
    def test_arm_and_thumb_instruction_modes(self):
        arm = dbaa.disassemble(bytes.fromhex("0100a0e31eff2fe1"), 0x080000C0, "arm")
        thumb = dbaa.disassemble(bytes.fromhex("01207047"), 0x08000100, "thumb")
        self.assertIn("mov", arm[2])
        self.assertIn("bx", arm[3])
        self.assertIn("movs", thumb[2])
        self.assertIn("bx", thumb[3])

    def test_wrong_alignment(self):
        for data, address, mode in ((bytes(4), 0x080000C2, "arm"), (bytes(3), 0x08000100, "thumb")):
            with self.assertRaises(ValueError):
                dbaa.disassemble(data, address, mode)


if __name__ == "__main__":
    unittest.main()
