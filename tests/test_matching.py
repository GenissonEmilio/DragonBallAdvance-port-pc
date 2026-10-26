"""Integration checks for the actual C -> linked ARM binary -> ROM comparison."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/matching.json").read_text(encoding="utf-8"))
READY = (ROOT / "baserom.gba").is_file() and (ROOT / CONFIG["compiler"]["path"]).is_file()
READY_ALL = READY and all((ROOT / profile["path"]).is_file()
                          for profile in CONFIG.get("compiler_profiles", {}).values())


class MatchingTests(unittest.TestCase):
    def run_match(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "tools/match.py"), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True)

    def test_wrong_rom_is_rejected_before_compilation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "wrong.gba"
            path.write_bytes(bytes(0x200))
            out = Path(temp) / "out"
            result = self.run_match("--rom", path, "--out-dir", out)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("exact USA ROM SHA-1", result.stderr)
            self.assertFalse((out / "report.json").exists())

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_c_compilation_matches_instructions_and_literal(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "positive match"
            result = self.run_match("--out-dir", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertTrue(report["equal"])
            self.assertEqual(report["candidate_size"], 28)
            self.assertEqual(report["different_bytes"], 0)
            self.assertFalse(report["assembly_postprocessing"])
            self.assertFalse(report["remaining_relocations"])
            rom = (ROOT / "baserom.gba").read_bytes()
            self.assertEqual((out / "state_counter.bin").read_bytes(), rom[0x144C:0x1468])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_c_is_recompiled_and_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "negative match"
            candidate = Path(temp) / "changed source.c"
            source = (ROOT / "src/state_counter.c").read_text()
            self.assertEqual(source.count("word10++;"), 1)
            candidate.write_text(source.replace("word10++;", "word10 += 2;"))
            result = self.run_match("--source", candidate, "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_uncompared_allocated_sections_are_rejected(self):
        source = (ROOT / "src/state_counter.c").read_text()
        allocations = [
            "DbaaU32 unexpected_initialized = 0x11223344;",
            "const DbaaU32 unexpected_constant = 0x11223344;",
            "DbaaU32 unexpected_zero;",
        ]
        with tempfile.TemporaryDirectory() as temp:
            for index, declaration in enumerate(allocations):
                with self.subTest(declaration=declaration):
                    candidate = Path(temp) / f"extra_{index}.c"
                    candidate.write_text(source + "\n" + declaration + "\n")
                    out = Path(temp) / f"extra_{index}"
                    result = self.run_match("--source", candidate, "--out-dir", out)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn("uncompared allocated section:", result.stderr)
                    self.assertFalse((out / "report.json").exists())

    @unittest.skipUnless(READY_ALL, "requires user's USA ROM and all local matching compilers")
    def test_all_targets_match_complete_linked_sections(self):
        functions = json.loads((ROOT / "config/functions.usa.json").read_text())
        targets = {"state_counter": CONFIG["target"]}
        targets.update({entry["id"]: entry for entry in functions["functions"]})
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "all targets"
            result = self.run_match("--all", "--out-dir", out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual({row["id"] for row in summary}, set(targets))
            rom = (ROOT / "baserom.gba").read_bytes()
            for row in summary:
                with self.subTest(target=row["id"]):
                    target = targets[row["id"]]
                    size = target.get("size") or target["instruction_bytes"] + target["literal_bytes"]
                    offset = int(target["address"], 0) - 0x08000000
                    report = row["report"]
                    profile_id = target.get("compiler_profile", "agbcc")
                    profile = CONFIG["compiler"] if profile_id == "agbcc" else CONFIG["compiler_profiles"][profile_id]
                    self.assertEqual(row["returncode"], 0)
                    self.assertTrue(report["equal"])
                    self.assertEqual(report["candidate_size"], size)
                    self.assertEqual(report["different_bytes"], 0)
                    self.assertEqual(report["compiler_flags"],
                                     target.get("compiler_flags", profile["flags"]))
                    self.assertEqual(report["compiler_profile"], profile_id)
                    self.assertEqual(report["compiler_path"], profile["path"])
                    self.assertEqual(report["compiler_executable_sha256"],
                                     hashlib.sha256((ROOT / profile["path"]).read_bytes()).hexdigest())
                    for field, path in [("matching_config_sha256", "config/matching.json"),
                                        ("matching_tool_sha256", "tools/match.py")]:
                        self.assertEqual(report[field], hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
                    self.assertEqual(report["reference_sha256"], report["candidate_sha256"])
                    self.assertFalse(report["assembly_postprocessing"])
                    self.assertFalse(report["remaining_relocations"])
                    self.assertEqual((out / row["id"] / f"{row['id']}.bin").read_bytes(),
                                     rom[offset:offset + size])
                    if "label_metadata" in target:
                        metadata = report["label_metadata"]
                        self.assertEqual(metadata["size"], target["label_metadata"]["entries"] * 4)
                        self.assertFalse(metadata["allocatable"])
                        self.assertFalse(metadata["executable"])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_callee_fails_after_thumb_relocation(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed callee.c"
            source = (ROOT / "src/game_entry.c").read_text()
            self.assertEqual(source.count("Game_Bootstrap();"), 1)
            candidate.write_text(source.replace("Game_Bootstrap();", "Runtime_Initialize();"))
            out = Path(temp) / "negative call"
            result = self.run_match("--target", "game_entry", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertFalse(report["remaining_relocations"])
            self.assertEqual(report["candidate_size"], 12)

    def test_all_targets_do_not_reuse_stale_success_reports(self):
        functions = json.loads((ROOT / "config/functions.usa.json").read_text())
        target_ids = ["state_counter", *(entry["id"] for entry in functions["functions"])]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "stale"
            for target_id in target_ids:
                folder = out / target_id
                folder.mkdir(parents=True)
                (folder / "report.json").write_text('{"equal": true}')
            wrong = Path(temp) / "wrong.gba"
            wrong.write_bytes(bytes(0x200))
            result = self.run_match("--all", "--rom", wrong, "--out-dir", out)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(len(summary), len(target_ids))
            for row in summary:
                self.assertEqual(row["returncode"], 2)
                self.assertIsNone(row["report"])

    def test_candidate_manifest_cannot_change_rom_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "wrong manifest.json"
            manifest.write_text(json.dumps({"rom_sha1": "0" * 40, "functions": []}))
            result = self.run_match("--function-map", manifest)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("maps must belong to the configured ROM", result.stderr)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_unknown_compiler_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "unknown compiler.json"
            manifest.write_text(json.dumps({"rom_sha1": CONFIG["rom_sha1"], "functions": [{
                "id": "unknown_compiler", "name": "Game_Entry", "source": "src/game_entry.c",
                "address": "0x0800152C", "size": 12, "compiler_profile": "missing_profile"}]}))
            out = Path(temp) / "out"
            result = self.run_match("--function-map", manifest, "--target", "unknown_compiler", "--out-dir", out)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("unknown compiler profile: missing_profile", result.stderr)
            self.assertFalse((out / "report.json").exists())

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_candidate_manifest_is_forwarded_to_all_children(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "candidate manifest.json"
            manifest.write_text(json.dumps({"rom_sha1": CONFIG["rom_sha1"], "functions": [{
                "id": "candidate_wrapper", "name": "Game_Entry", "source": "src/game_entry.c",
                "address": "0x0800152C", "size": 12}]}))
            out = Path(temp) / "candidates"
            result = self.run_match("--function-map", manifest, "--all", "--out-dir", out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual({row["id"] for row in summary}, {"state_counter", "candidate_wrapper"})
            self.assertTrue(all(row["report"]["equal"] for row in summary))

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_dma_control_is_not_masked(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed DMA.c"
            source = (ROOT / "src/graphics_commit_dma.c").read_text()
            self.assertEqual(source.count("0x84000002"), 1)
            candidate.write_text(source.replace("0x84000002", "0x84000012"))
            out = Path(temp) / "negative DMA"
            result = self.run_match("--target", "graphics_commit_dma", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_background_pitch_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed background pitch.c"
            source = (ROOT / "src/graphics_clear_backgrounds.c").read_text()
            self.assertEqual(source.count("pitch=16<<size;"), 1)
            candidate.write_text(source.replace("pitch=16<<size;", "pitch=8<<size;"))
            out = Path(temp) / "negative background"
            result = self.run_match("--target", "graphics_clear_backgrounds", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_background_sprite_tile_size_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed background sprite tile size.c"
            source = (ROOT / "src/graphics_draw_background_sprites.c").read_text()
            self.assertEqual(source.count("int tileShift = 5;"), 1)
            candidate.write_text(source.replace("int tileShift = 5;", "int tileShift = 4;"))
            out = Path(temp) / "negative background sprite"
            result = self.run_match("--target", "graphics_draw_background_sprites", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)
            self.assertFalse(report["assembly_postprocessing"])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_background_queue_wrap_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed queue wrap.c"
            source = (ROOT / "src/graphics_process_background_queue.c").read_text()
            self.assertEqual(source.count("r0 = 0xfu;"), 1)
            candidate.write_text(source.replace("r0 = 0xfu;", "r0 = 0xeu;"))
            out = Path(temp) / "negative queue wrap"
            result = self.run_match("--target", "graphics_process_background_queue", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)
            self.assertEqual(report["compiler_flags"], ["-O1", "-mthumb-interwork"])
            self.assertFalse(report["assembly_postprocessing"])
            self.assertFalse(report["label_metadata"]["allocatable"])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_task_capacity_and_priority_mutations_fail_the_gate(self):
        source = (ROOT / "src/task_create.c").read_text()
        for old, new in [("gFreeTaskIndex < 128", "gFreeTaskIndex < 127"),
                         ("next->priority > priority", "next->priority >= priority")]:
            with self.subTest(change=new), tempfile.TemporaryDirectory() as temp:
                self.assertEqual(source.count(old), 1)
                candidate = Path(temp) / "changed task creation.c"
                candidate.write_text(source.replace(old, new))
                out = Path(temp) / "negative task"
                result = self.run_match("--target", "task_create", "--source", candidate, "--out-dir", out)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads((out / "report.json").read_text())
                self.assertFalse(report["equal"])
                self.assertGreater(report["different_bytes"], 0)
                self.assertFalse(report["assembly_postprocessing"])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_iwram_alignment_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            source = (ROOT / "src/iwram_alloc.c").read_text()
            self.assertEqual(source.count("size = (size + 3) / 4;"), 1)
            candidate = Path(temp) / "changed IWRAM allocation.c"
            candidate.write_text(source.replace("size = (size + 3) / 4;", "size = (size + 7) / 4;"))
            out = Path(temp) / "negative IWRAM"
            result = self.run_match("--target", "iwram_alloc", "--source", candidate, "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_ewram_coalescing_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            source = (ROOT / "src/ewram_free.c").read_text()
            self.assertEqual(source.count("if (fast->state > 0)"), 1)
            candidate = Path(temp) / "changed EWRAM release.c"
            candidate.write_text(source.replace("if (fast->state > 0)", "if (fast->state >= 0)"))
            out = Path(temp) / "negative EWRAM"
            result = self.run_match("--target", "ewram_free", "--source", candidate, "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)

    def assert_reset_service_mutation_is_rejected(self, target, old, new):
        source = (ROOT / "src" / f"{target}.c").read_text()
        self.assertEqual(source.count(old), 1)
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed reset service.c"
            candidate.write_text(source.replace(old, new))
            out = Path(temp) / "negative reset service"
            result = self.run_match("--target", target, "--source", candidate, "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)
            self.assertFalse(report["assembly_postprocessing"])
            self.assertFalse(report["remaining_relocations"])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_video_control_store_width_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "game_video_flags_clear", "DbaaU16 half08;", "DbaaU32 half08;")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_reset_enable_flag_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "reset_link", "gSystemFlags & 0x80000", "gSystemFlags & 0x40000")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_interrupt_mask_and_clear_size_fail_the_gate(self):
        for old, new in [("&= 0xFF3F", "&= 0xFF7F"),
                         ("gSerialAuxState, 0x05000003", "gSerialAuxState, 0x05000002")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("serial_start", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_player_pause_flag_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "music_player_stop", "player->status |= 0x80000000", "player->status |= 0x40000000")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_irq_handshake_and_switch_mutations_fail_the_gate(self):
        for old, new in [("second == 0x8002", "second == 0x8003"),
                         ("case 5:", "case 6:")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("serial_irq", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_irq_disable_mask_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "serial_irq", "&= 0xFF7F", "&= 0xFF3F")

    @unittest.skipUnless(READY_ALL, "requires user's USA ROM and all local matching compilers")
    def test_music_track_status_and_channel_masks_fail_the_gate(self):
        for old, new in [("mask = 0x80;", "mask = 0x40;"),
                         ("channelMask = 7;", "channelMask = 3;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("music_track_stop", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_packet_checksum_gate_and_stored_bit_fail_the_gate(self):
        for old, new in [("if (Serial_ValidatePacket())", "if (Serial_ValidatePacket() == 0)"),
                         (">> 8) & 1;", ">> 8) & 3;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("serial_process_packet", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_packet_echo_comparison_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "serial_process_packet", "gSerialPacketValue !=", "gSerialPacketValue ==")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_packet_checksum_nibble_range_fails_the_gate(self):
        for old, new in [("((index - 1) * 4)", "(index * 4)"),
                         ("checksum ^= (data >> ((index - 1) * 4)) & 0xF;",
                          "checksum ^= (data >> ((index - 1) * 4)) & 0x7;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("serial_validate_packet", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_serial_packet_payload_type_and_switch_mutations_fail_the_gate(self):
        for old, new in [("0xFFFFFF", "0xFFFFFE"), ("0x40000000", "0x30000000"),
                         ("case 5:", "case 6:")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("serial_make_packet", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sequence_create_priority_and_vram_fill_fail_the_gate(self):
        for old, new in [("0x14, 0x200", "0x14, 0x100"),
                         ("0x01006000", "0x01004000")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("sequence_create", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sequence_prepare_callback_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "sequence_prepare", "gCurrentTask->callback = Sequence_Finish;",
            "gCurrentTask->callback = Sequence_Run;")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sequence_skip_key_and_guard_mask_fail_the_gate(self):
        for old, new in [("gPressedKeys & 8", "gPressedKeys & 4"),
                         ("0x20080", "0x20000")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("sequence_run", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sequence_completion_sentinel_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "sequence_finish", "mode != 12", "mode != 11")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_sequence_fill_and_parent_state_fail_the_gate(self):
        for old, new in [("0x01000016", "0x01000015"),
                         ("sequence->state++;", "sequence->state += 2;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("boot_sequence_initialize", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_after_boot_next_sequence_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "sequence_after_boot", "Func_080C863C(0x4D, 0, 1, 0)",
            "Func_080C863C(0x4C, 0, 1, 0)")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_screen_fade_priority_and_delay_fail_the_gate(self):
        for old, new in [("0xFFFE", "0xFFFD"),
                         ("data->delay = 6;", "data->delay = 5;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("fade_create", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_screen_fade_brightness_and_signed_clamp_fail_the_gate(self):
        for target, old, new in [
            ("fade_commit", "data->value >> 8", "data->value >> 7"),
            ("fade_run", "if (data->value < data->target)", "if (data->value <= data->target)")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_video_mode_and_vram_fill_fail_the_gate(self):
        for old, new in [("gDisplayControlShadow = 0x140", "gDisplayControlShadow = 0x100"),
                         ("0x0100C000", "0x01008000")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("boot_sequence_run", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_finish_parent_state_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "boot_sequence_finish", "data->sequence->state--;", "data->sequence->state++;")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_input_and_completion_gate_fail_the_gate(self):
        for old, new in [("gPressedKeys & 0xB", "gPressedKeys & 8"),
                         ("data->flags < 0", "data->flags > 0")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("boot_sequence_update", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_screen_limit_and_terminal_flag_fail_the_gate(self):
        for old, new in [("data->screen > 3", "data->screen > 2"),
                         ("0x80000000", "0x40000000")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("boot_sequence_advance", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_graphics_stride_and_palette_path_fail_the_gate(self):
        for target, old, new in [
            ("boot_sequence_load_screen", "row * 32", "row * 16"),
            ("boot_sequence_load_screen", "gSystemFlags & 0x10000", "gSystemFlags & 0x20000"),
            ("boot_sequence_clear_screen", "0x01000400", "0x01000200")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_fade_direction_and_duration_fail_the_gate(self):
        for target, old, new in [
            ("boot_sequence_fade_in", "16 - (data->timer << 4)", "16 + (data->timer << 4)"),
            ("boot_sequence_fade_out", "data->timer << 4", "data->timer << 3"),
            ("boot_sequence_begin_fade_out", "fadeOutFrames >> 1", "fadeOutFrames >> 2")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_phase_callbacks_fail_the_gate(self):
        for target, old, new in [
            ("boot_sequence_start_screen", "data->phase = BootSequence_FadeIn;",
             "data->phase = BootSequence_FadeOut;"),
            ("boot_sequence_begin_hold", "data->phase = BootSequence_Hold;",
             "data->phase = BootSequence_Advance;")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_boot_child_pause_and_hold_time_fail_the_gate(self):
        for target, old, new in [
            ("boot_sequence_begin_pause", "duration >>= 1", "duration >>= 2"),
            ("boot_sequence_hold", "data->timer >= data->duration", "data->timer > data->duration")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_task_size_and_zero_fill_fail_the_gate(self):
        for old, new in [("0x1EC, 0x200", "0x1E8, 0x200"),
                         ("0x010000F6", "0x010000F5")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_initialize", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_video_and_allocator_restore_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_run", "gGameHalf03002BEC = 0x400", "gGameHalf03002BEC = 0x200"),
            ("post_boot_run", "gBgControlShadow[1] = 0x5C04", "gBgControlShadow[1] = 0x5C00"),
            ("post_boot_finish", "0x06014000", "0x06010000")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_destructor_and_parent_state_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_destroy", "0x01000000", "0x02000000"),
            ("post_boot_destroy", "if (data->child3)", "if (!data->child3)"),
            ("post_boot_finish", "data->sequence->state--;", "data->sequence->state++;")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_frame_and_input_guards_fail_the_gate(self):
        for old, new in [("data->elapsed++;", "data->elapsed += 2;"),
                         ("gPressedKeys & 0xB", "gPressedKeys & 8"),
                         ("data->flags & 0x20", "data->flags & 0x10")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_update", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_sprite_count_and_order_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_prepare_sprites", "i < 9", "i < 8"),
            ("post_boot_prepare_sprites", "sprite->order = 0x440", "sprite->order = 0x400"),
            ("post_boot_free_sprites", "i < 9", "i < 8")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_vram_tile_rounding_and_block_stride_fail_the_gate(self):
        for target, old, new in [
            ("vram_allocate_tiles", "value + 3", "value + 7"),
            ("vram_allocate_tiles", "i * 128", "i * 64"),
            ("vram_free_tiles", ">> 7", ">> 6")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_song_player_record_stride_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "music_start_song", "entry->player * 12", "entry->player * 8")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_timeline_and_graphics_selection_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_enable_backgrounds", "data->elapsed >=", "data->elapsed >"),
            ("post_boot_disable_backgrounds", "data->phase = PostBoot_Phase3;",
             "data->phase = PostBoot_Phase4;"),
            ("post_boot_phase3", "PostBoot_LoadBackground(3)", "PostBoot_LoadBackground(2)"),
            ("post_boot_load_tiles", "index != 8", "index != 7")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_skip_task_priority_and_duration_fail_the_gate(self):
        for old, new in [("16, 0x1000, 0", "16, 0x800, 0"),
                         ("data->duration = 20", "data->duration = 21")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_create_skip", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_skip_wait_and_completion_flag_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_skip_run", "data->parent->flags & 0x10", "data->parent->flags & 0x20"),
            ("post_boot_skip_fade", "0x40000000", "0x80000000"),
            ("post_boot_skip_fade", "data->elapsed >= data->duration", "data->elapsed > data->duration")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_loader_signed_fallback_and_special_index_fail_the_gate(self):
        for old, new in [("(int)r0 < (int)0x0u", "(int)r0 >= (int)0x0u"),
                         ("r2 != 0xAu", "r2 == 0xAu")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_background", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_loader_mirror_and_row_stride_fail_the_gate(self):
        for old, new in [("r0 = r0 ^ r6;", "r0 = r0 | r6;"),
                         ("r1 = r4 << 0x6u;", "r1 = r4 << 0x5u;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_background", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_loader_palette_nibble_preservation_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "post_boot_load_background", "r6 = 0xFFFu;", "r6 = 0x3FFu;")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_loader_palette_service_and_dma_enable_fail_the_gate(self):
        for old, new in [("r0 = r0 << 0x9u;", "r0 = r0 << 0x8u;"),
                         ("r1 = r1 << 0x18u;", "r1 = r1 << 0x17u;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_background", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase4_time_limit_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "post_boot_phase4", "data->elapsed >=", "data->elapsed >")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase4_background_pair_and_next_callback_fail_the_gate(self):
        for old, new in [("data->backgrounds[2]", "data->backgrounds[1]"),
                         ("data->phase = PostBoot_Phase5;", "data->phase = PostBoot_Phase3;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase4", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase5_background_and_callback_fail_the_gate(self):
        for old, new in [("PostBoot_LoadBackground(4)", "PostBoot_LoadBackground(3)"),
                         ("data->phase = PostBoot_Phase6;", "data->phase = PostBoot_Phase7;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase5", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_three_background_selection_fails_the_gate(self):
        for target, old, new in [
            ("post_boot_phase6", "data->backgrounds[3]", "data->backgrounds[2]"),
            ("post_boot_phase7", "data->backgrounds[4]", "data->backgrounds[5]")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_later_background_ids_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase8", "data->backgrounds[0]", "data->backgrounds[1]"),
            ("post_boot_phase9", "PostBoot_LoadBackground(5)", "PostBoot_LoadBackground(4)"),
            ("post_boot_phase12", "PostBoot_LoadBackground(6)", "PostBoot_LoadBackground(5)"),
            ("post_boot_phase16", "PostBoot_LoadBackground(7)", "PostBoot_LoadBackground(6)")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_later_timeline_and_skip_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase10", "data->elapsed >=", "data->elapsed >"),
            ("post_boot_phase14", "data->backgrounds[6]", "data->backgrounds[5]"),
            ("post_boot_phase17", "data->flags & 1", "data->flags & 2")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_window_clear_count_fails_the_gate(self):
        for old, new in [("0xDFFF", "0xBFFF"), ("0x01000006", "0x01000005")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase15", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_fade_wait_flags_fail_the_gate(self):
        for old, new in [("flags & 0x10", "flags & 0x20"), ("flags & 1", "flags & 2")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase18", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_fade_creation_direction_and_timing_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase19", "PostBoot_StartFade(data, 1)", "PostBoot_StartFade(data, 0)"),
            ("post_boot_start_fade", " - parent->elapsed", " + parent->elapsed"),
            ("post_boot_create_fade", "20, 0x180, 0", "20, 0x200, 0"),
            ("post_boot_create_fade", "<< 8) / config->duration", "<< 7) / config->duration")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_fade_step_and_completion_fail_the_gate(self):
        for old, new in [("data->elapsed >= data->duration", "data->elapsed > data->duration"),
                         ("data->parent->flags |= 0x20", "data->parent->flags |= 0x40")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_fade_run", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_tile_chunk_count_and_size_fail_the_gate(self):
        for old, new in [("data->tileChunk > 5", "data->tileChunk > 4"),
                         ("0x04000400", "0x04000200")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_copy_tile_chunk", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_background_map_clear_size_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "post_boot_clear_background_map", "0x01000800", "0x01000400")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase21_completion_and_background_fail_the_gate(self):
        for old, new in [("data->flags & 0x40", "data->flags & 0x20"),
                         ("data->backgrounds[7]", "data->backgrounds[8]"),
                         ("data->phase = PostBoot_Phase22;", "data->phase = PostBoot_Phase24;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase21", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase22_time_and_services_fail_the_gate(self):
        for old, new in [("data->elapsed >=", "data->elapsed >"),
                         ("PostBoot_LoadMap(8)", "PostBoot_LoadMap(9)"),
                         ("PostBoot_LoadPalette(8)", "PostBoot_LoadPalette(9)")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase22", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase23_wait_and_skip_fail_the_gate(self):
        for old, new in [("flags & 0x10", "flags & 0x20"), ("flags & 1", "flags & 2")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase23", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_later_fade_and_clear_guards_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase24", "PostBoot_StartFade(data, 1)", "PostBoot_StartFade(data, 0)"),
            ("post_boot_phase25", "data->backgrounds[8]", "data->backgrounds[7]"),
            ("post_boot_phase26", "data->flags & 1", "data->flags & 2")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_final_background_selection_fails_the_gate(self):
        for target, old, new in [
            ("post_boot_phase28", "PostBoot_LoadBackground(9)", "PostBoot_LoadBackground(8)"),
            ("post_boot_phase29", "PostBoot_LoadBackground(10)", "PostBoot_LoadBackground(9)")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_map_fallback_and_stride_fail_the_gate(self):
        for old, new in [("entry->backgroundId >= 0", "entry->backgroundId > 0"),
                         ("mapVram + row * 32,", "mapVram + row * 16,")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_map", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_map_mirror_and_palette_mask_fail_the_gate(self):
        for old, new in [("*source ^ 0x400", "*source | 0x400"),
                         ("*destination & 0xFFF", "*destination & 0x3FF")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_map", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_palette_service_and_dma_fail_the_gate(self):
        for old, new in [("gSystemFlags & 0x10000", "gSystemFlags & 0x20000"),
                         ("0x80000000", "0x40000000")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_palette", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_background_priority_and_scroll_fail_the_gate(self):
        for old, new in [("0xFFFC", "0xFFF8"),
                         ("gBackgroundScroll[bg][1] = entry->scrollY;",
                          "gBackgroundScroll[bg][1] = entry->scrollX;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_apply_background", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_special_palette_selector_fails_the_gate(self):
        self.assert_reset_service_mutation_is_rejected(
            "post_boot_special_background", "PostBoot_LoadSpecialPalette(entry->sourcePalette);",
            "PostBoot_LoadSpecialPalette(entry->destinationPalette);")

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_special_tiles_and_map_table_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_load_special_tiles", 'limit __asm__("r8") = 9', 'limit __asm__("r8") = 8'),
            ("post_boot_load_special_map", "gPostBootMapRows[9 - row]", "gPostBootMapRows[8 - row]")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_special_blue_channel_and_fill_fail_the_gate(self):
        for old, new in [("0x7C00", "0x3E0"), ("DbaaU8 count = 8", "DbaaU8 count = 7")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_load_special_palette", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase30_skip_and_time_fail_the_gate(self):
        for old, new in [("data->flags & 2", "data->flags & 1"),
                         ("data->elapsed >=", "data->elapsed >")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase30", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase30_and31_fade_config_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase30", "config.control = 0xEF", "config.control = 0xFF"),
            ("post_boot_phase31", "config.duration = 40", "config.duration = 41"),
            ("post_boot_phase31", "| 0xC0", "| 0x80")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_curtain_task_size_and_window_fail_the_gate(self):
        for old, new in [("24, 0x300, 0", "24, 0x200, 0"),
                         ("0x0100000C", "0x0100000B"),
                         ("gWindowShadow[2] = 0xFF", "gWindowShadow[2] = 0xEF")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_create_curtain", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_curtain_initial_motion_and_background_fail_the_gate(self):
        for old, new in [("data->velocityX = -608", "data->velocityX = -576"),
                         ("parent->backgrounds[9]", "parent->backgrounds[10]")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_create_curtain", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_curtain_wait_and_signal_flags_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_curtain_wait", "data->parent->elapsed > 259", "data->parent->elapsed > 258"),
            ("post_boot_curtain_move", "data->parent->flags |= 0x400", "data->parent->flags |= 0x800"),
            ("post_boot_curtain_move", "data->parent->flags |= 0x200", "data->parent->flags |= 0x100")]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_curtain_window_threshold_and_stride_fail_the_gate(self):
        for old, new in [("<= 71", "<= 72"),
                         ("next = ((DbaaU32)drawX << 16) + 0xFFE00000;",
                          "next = ((DbaaU32)drawX << 16) + 0xFFC00000;")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_curtain_move", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_curtain_hold_range_and_stride_fail_the_gate(self):
        for old, new in [("<= 271", "<= 239"), ("0x00200000", "0x00400000")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_curtain_hold", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_next_backgrounds_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase32", "PostBoot_LoadBackground(11)", "PostBoot_LoadBackground(10)"),
            ("post_boot_phase33", "PostBoot_LoadBackground(12)", "PostBoot_LoadBackground(11)"),
            ("post_boot_phase37", "PostBoot_LoadBackground(13)", "PostBoot_LoadBackground(12)")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_scroll_pair_time_and_slot_fail_the_gate(self):
        for old, new in [("data->elapsed >=", "data->elapsed >"),
                         ("PostBoot_CreateScroll(data, 12, 1, duration)",
                          "PostBoot_CreateScroll(data, 12, 0, duration)")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_phase34", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_scroll_task_and_acceleration_fail_the_gate(self):
        for old, new in [("32, 0x400, 0", "32, 0x300, 0"),
                         (" << 17;", " << 16;"),
                         ("duration * duration", "duration + duration")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_create_scroll", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_scroll_tick_and_sibling_completion_fail_the_gate(self):
        for old, new in [("data->position += data->velocity;", "data->position -= data->velocity;"),
                         ("data->elapsed >= data->duration", "data->elapsed > data->duration"),
                         ("(data->slot + 1) & 1", "(data->slot + 0) & 1")]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected("post_boot_scroll_run", old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_scroll_phase_wait_and_disable_fail_the_gate(self):
        for target, old, new in [
            ("post_boot_phase35", "data->elapsed >=", "data->elapsed >"),
            ("post_boot_phase36", "data->backgrounds[12]", "data->backgrounds[13]")]:
            with self.subTest(target=target):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase38_background_and_next_phase_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_phase38', 'PostBoot_LoadBackground(14)', 'PostBoot_LoadBackground(13)'),
            ('post_boot_phase38', 'PostBoot_Phase39;', 'PostBoot_Phase40;'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_phase39_pair_and_timing_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_phase39', 'data->elapsed >=', 'data->elapsed >'),
            ('post_boot_phase39', 'PostBoot_CreateScroll(data, 14, 1, duration)', 'PostBoot_CreateScroll(data, 14, 0, duration)'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_final_fades_skip_and_control_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_phase41', 'data->flags & 2', 'data->flags & 1'),
            ('post_boot_phase47', 'config.control = 0xBF', 'config.control = 0xFF'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_final_display_and_cleanup_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_phase42', '0xF0FF', '0xF1FF'),
            ('post_boot_phase43', 'Task_Destroy(data->child0);', 'Task_Destroy(data->child3);'),
            ('post_boot_phase44', '0x1040', '0x1000'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_final_ring_wait_and_completion_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_phase46', 'data->flags & 0x1000', 'data->flags & 0x800'),
            ('post_boot_phase48', '0x40000000', '0x20000000'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_task_size_and_sprite_base_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_create_ring', '52, 0x400, 0', '52, 0x300, 0'),
            ('post_boot_create_ring', 'parent->sprites[2]', 'parent->sprites[1]'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_step_sync_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_ring_run', 'data->parent->elapsed;', 'data->parent->flags;'),
            ('post_boot_ring_run', 'data->phase(data) == 0', 'data->phase(data) != 0'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_contraction_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_ring_init_contract', '200 << 16', '180 << 16'),
            ('post_boot_ring_init_contract', '0xFF6E0000', '0xFF700000'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_spin_timing_and_acceleration_fails_the_gate(self):
        for target, old, new in [('post_boot_ring_spin', 'data->elapsed >=', 'data->elapsed >'), ('post_boot_ring_init_spin', '0xC000', '0x6000')]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_release_flag_and_motion_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_ring_release', '~0x1000', '~0x800'),
            ('post_boot_ring_release', 'data->angularVelocity >>= 2;', 'data->angularVelocity >>= 3;'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_integration_and_draw_count_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_ring_step', 'data->radius += data->radialVelocity;', 'data->radius -= data->radialVelocity;'),
            ('post_boot_ring_draw', 'i < 7', 'i < 6'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_post_boot_ring_geometry_fails_the_gate(self):
        for target, old, new in [
            ('post_boot_position_ring', '146 * i + 110', '146 * i + 109'),
            ('post_boot_position_ring', '+ 120;', '+ 119;'),
            ('post_boot_position_ring', 'phase + 256', 'phase + 255'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sprite_frame_and_stride_fails_the_gate(self):
        for target, old, new in [
            ('graphics_draw_sprite', 'frame == (DbaaU32)-1', 'frame == (DbaaU32)-2'),
            ('graphics_draw_sprite', 'frame * 12;', 'frame * 16;'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sprite_affine_and_camera_flags_fails_the_gate(self):
        for target, old, new in [
            ('graphics_draw_sprite', 'loaded & 0x20000', 'loaded & 0x10000'),
            ('graphics_draw_sprite', 'if (flags & 0x20)', 'if (flags & 0x10)'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sprite_screen_bounds_fails_the_gate(self):
        for target, old, new in [
            ('graphics_draw_sprite', 'screenX > 240', 'screenX > 239'),
            ('graphics_draw_sprite', 'y > 160', 'y > 159'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sprite_order_and_transfer_gate_fails_the_gate(self):
        for target, old, new in [
            ('graphics_draw_sprite', '0x7C0', '0x780'),
            ('graphics_draw_sprite', 'state & IN_REGISTER("r0", 0x04000000)', 'state & IN_REGISTER("r0", 0x02000000)'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sprite_contiguous_runs_and_size_wrap_fails_the_gate(self):
        for target, old, new in [
            ('graphics_draw_sprite', 'begin + size == next', 'begin + size != next'),
            ('graphics_draw_sprite', 'size = (DbaaU16)combined;', 'size = (DbaaU8)combined;'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_oam_capacity_and_order_clamp_fails_the_gate(self):
        for target, old, new in [
            ('graphics_allocate_oam', 'order > 31', 'order > 30'),
            ('graphics_allocate_oam', '(DbaaS8)gOamFreeIndex < 0', '(DbaaS8)gOamFreeIndex <= 0'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_oam_links_and_returned_slot_fails_the_gate(self):
        for target, old, new in [
            ('graphics_allocate_oam', '(DbaaU8)gOamOrderTails[order]', '(DbaaU8)gOamOrderHeads[order]'),
            ('graphics_allocate_oam', 'gOamFreeIndex - 1', 'gOamFreeIndex - 0'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_palette_channels_and_count_fails_the_gate(self):
        for target, old, new in [
            ('graphics_load_palette', '0x7C00', '0x3E0'),
            ('graphics_load_palette', 'color & 0x1F', 'color & 0xF'),
            ('graphics_load_palette', '(DbaaU16)IN_REGISTER("r2", count)', '(DbaaU8)IN_REGISTER("r2", count)'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_palette_callback_and_dirty_flag_fails_the_gate(self):
        for target, old, new in [
            ('graphics_load_palette', 'if (callback)', 'if (!callback)'),
            ('graphics_load_palette', 'gSystemFlags |= 1;', 'gSystemFlags |= 2;'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_memset_alignment_chunks_and_tail_fails_the_gate(self):
        for target, old, new in [
            ('runtime_memset', '((DbaaU32)bytes & 3)', '((DbaaU32)bytes & 1)'),
            ('runtime_memset', 'size -= 16;', 'size -= 8;'),
            ('runtime_memset', 'if (!remaining)', 'if (remaining == 1)'),
        ]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_reset_and_end_flag_fails_the_gate(self):
        for old, new in [('sprite->previousVariant != sprite->variant', 'sprite->previousVariant == sprite->variant'),
                         ('sprite->flags &= ~0x4000;', 'sprite->flags &= ~0x2000;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_update_animation', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_signed_delay_and_speed_fails_the_gate(self):
        for old, new in [('sprite->animationDelay > 0', 'sprite->animationDelay >= 0'),
                         ('sprite->animationDelay -= sprite->speed << 4;', 'sprite->animationDelay -= sprite->speed << 3;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_update_animation', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_command_dispatch_and_reload_fails_the_gate(self):
        for old, new in [('gAnimationCommands[~*command]', 'gAnimationCommands[-*command]'),
                         ('if (result != -1)', 'if (result != -2)')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_update_animation', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_duration_and_tile_dirty_flag_fails_the_gate(self):
        for old, new in [('(*command << 8)', '(*command << 7)'),
                         ('sprite->flags |= 0x04000000;', 'sprite->flags |= 0x02000000;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_update_animation', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_tile_queue_and_signed_index_fails_the_gate(self):
        for old, new in [('if (index < 0)', 'if (index > 0)'),
                         ('gVramQueueWriteIndex + 1) & 0x7F', 'gVramQueueWriteIndex + 1) & 0x3F')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_command_tiles', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_palette_mode_and_dma_width_fails_the_gate(self):
        for old, new in [('flags & 0x20000', 'flags & 0x10000'),
                         ('0x80000000 | command->count', '0x84000000 | command->count')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_command_palette', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_hitbox_copy_degenerate_and_flip_fails_the_gate(self):
        for old, new in [('0x84000002', '0x84000001'),
                         ('bytes[8] == bytes[10]', 'bytes[8] != bytes[10]'),
                         ('sprite->flags & 0x800', 'sprite->flags & 0x400')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sprite_command_hitbox', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_command_flow_and_opaque_return_fails_the_gate(self):
        for target, old, new in [('sprite_command_jump_back', '-= command[1]', '+= command[1]'),
                                 ('sprite_command_switch', 'return -1;', 'return 1;'),
                                 ('sprite_command_reserved9', 'return (int)command;', 'return 1;')]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_animation_priority_and_order_bits_fails_the_gate(self):
        for target, old, new in [('sprite_command_priority', '~0x3000', '~0x1000'),
                                 ('sprite_command_order', 'command[1] << 6', 'command[1] << 5')]:
            with self.subTest(target=target, change=new):
                self.assert_reset_service_mutation_is_rejected(target, old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_obj_palette_callback_and_dirty_flag_fails_the_gate(self):
        for old, new in [('if (callback)', 'if (!callback)'),
                         ('gSystemFlags |= 2;', 'gSystemFlags |= 1;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('graphics_load_obj_palette', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_start_lock_and_priority_fails_the_gate(self):
        for old, new in [('player->lock != 0x68736D53', 'player->lock == 0x68736D53'),
                         ('player->songPriority > priority', 'player->songPriority >= priority')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_player_start', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_start_track_bounds_and_states_fails_the_gate(self):
        for old, new in [('if (i >= player->trackCount)', 'if (i > player->trackCount)'),
                         ('held __asm__("r0") = 0xC0', 'held __asm__("r0") = 0x80'),
                         ('track->status = 0;', 'track->status = 1;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_player_start', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_start_tempo_and_mode_fails_the_gate(self):
        for old, new in [('player->tempo = 150;', 'player->tempo = 149;'),
                         ('mode __asm__("r0") = 0x80', 'mode __asm__("r0") = 0x40')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_player_start', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_open_count_lock_and_chain_fails_the_gate(self):
        for old, new in [('count > 16', 'count > 15'),
                         ('sound->lock != 0x68736D53', 'sound->lock == 0x68736D53'),
                         ('sound->firstPlayer = player;', 'sound->firstPlayer = player->nextPlayer;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_player_open', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_vsync_off_guard_dma_and_buffer_fails_the_gate(self):
        for old, new in [('0x68736D53U > 1', '0x68736D53U > 0'),
                         ('IO32(0x040000C4) & 0x02000000', 'IO32(0x040000C4) & 0x01000000'),
                         ('0x05000318', '0x05000317')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_vsync_off', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_vsync_on_guard_and_lock_restore_fails_the_gate(self):
        for old, new in [('lock != 0x68736D53', 'lock == 0x68736D53'),
                         ('lock - 10', 'lock - 9')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_vsync_on', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_frequency_rate_and_timer_fails_the_gate(self):
        for old, new in [('597275 * samples + 5000', '597274 * samples + 5000'),
                         ('280896 / samples', '280895 / samples')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_set_frequency', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_frequency_index_pcm_and_scanline_fails_the_gate(self):
        for old, new in [('offset = index - 1;', 'offset = index - 0;'),
                         ('1584 / samples', '1583 / samples'),
                         ('0x04000006 == 159', '0x04000006 == 158')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_set_frequency', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_initialize_dma_repeat_and_stop_fails_the_gate(self):
        for old, new in [('IO32(0x040000C4) & 0x02000000', 'IO32(0x040000C4) & 0x01000000'),
                         ('IO32(0x040000D0) = 0x84400004;', 'IO32(0x040000D0) = 0x84000004;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_initialize', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_initialize_buffers_clear_and_frequency_fails_the_gate(self):
        for old, new in [('(DbaaU32)sound + 0x350', '(DbaaU32)sound + 0x354'),
                         ('0x050003EC', '0x050003EB'),
                         ('Sound_SetFrequency(0x40000)', 'Sound_SetFrequency(0x50000)')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_initialize', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_initialize_defaults_and_callback_fails_the_gate(self):
        for old, new in [('sound->channels = 8;', 'sound->channels = 7;'),
                         ('sound->volume = 15;', 'sound->volume = 14;'),
                         ('sound->callback38 = Sound_UpdateTrack;', 'sound->callback38 = Sound_Dummy;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_initialize', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_extend_lock_and_stereo_setup_fails_the_gate(self):
        for old, new in [('lock != 0x68736D53', 'lock == 0x68736D53'),
                         ('(volatile DbaaU8 *)stereo = 0x77', '(volatile DbaaU8 *)stereo = 0x33')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_extend', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_extend_commands_and_clear_size_fails_the_gate(self):
        for old, new in [('gSoundCommands[8] = SoundCommand_BFAC;', 'gSoundCommands[8] = Sound_Dummy;'),
                         ('(void (*)(void))MusicTrack_Stop;', '(void (*)(void))Sound_Dummy;'),
                         ('0x05000040', '0x0500003F')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_extend', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_sound_extend_channel_ids_masks_and_max_lines_fails_the_gate(self):
        for old, new in [('last[1] = 4;', 'last[1] = 3;'),
                         ('last[0x1C] = 0x88;', 'last[0x1C] = 0x44;'),
                         ('(DbaaU32)&gSoundDefaultMaxLines;', '(DbaaU32)&gSoundDefaultMaxLines + 1;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('sound_extend', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_stop_channel_and_wave_disable_fails_the_gate(self):
        for old, new in [('case 1:', 'case 0:'),
                         ('(volatile DbaaU8 *)0x04000070 = 0;', '(volatile DbaaU8 *)0x04000070 = 0x80;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_stop', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_frequency_noise_and_tone_limits_fails_the_gate(self):
        for old, new in [('key <= 20', 'key <= 19'), ('key > 59', 'key > 58'),
                         ('key <= 35', 'key <= 34'), ('key > 130', 'key > 129')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_frequency', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_frequency_signed_period_and_interpolation_fails_the_gate(self):
        for old, new in [('register const DbaaS16 *periods __asm__("r4");', 'register const DbaaU16 *periods __asm__("r4");'),
                         ('IN_REGISTER("r0", key + 1)', 'IN_REGISTER("r0", key + 0)')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_frequency', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_volume_stereo_clamp_and_envelope_fails_the_gate(self):
        for old, new in [('right >= left', 'right > left'), ('value > 15', 'value > 14'),
                         ('channel[0x1B] = 0xFF;', 'channel[0x1B] = 0x0F;'),
                         ('* volume + 15', '* volume + 14')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_update_volume', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_main_counter_and_channel_count_fail_the_gate(self):
        for old, new in [('a = (14);', 'a = (13);'),
                         ('if (channel <= 4)', 'if (channel <= 3)')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_update', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_main_registers_and_wave_copy_fail_the_gate(self):
        for old, new in [('a = (0x04000060);', 'a = (0x04000061);'),
                         ('H(c + 12)', 'H(c + 8)'),
                         ('W(0x28) = c;', 'W(0x24) = c;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_update', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_main_state_and_signed_decay_fail_the_gate(self):
        for old, new in [('a = (0xC7);', 'a = (0xC3);'),
                         ('decayZero = 0;', 'decayZero = 1;'),
                         ('if ((int)a > (int)b)', 'if (a > b)')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_update', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_main_echo_rounding_and_repeat_fail_the_gate(self):
        for old, new in [('a = (a + 255);', 'a = (a + 254);'),
                         ('a = (hw.counter);', 'a = (hw.counter + 1);')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_update', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_cgb_main_pwm_rounding_and_stereo_fail_the_gate(self):
        for old, new in [('if ((int)a > 0x3F)', 'if ((int)a > 0x3E)'),
                         ('b = (0x7FC);', 'b = (0x7FE);'),
                         ('b = (0x04000081);', 'b = (0x04000080);')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('cgb_update', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_fade_countdown_mode_and_step_fail_the_gate(self):
        for old, new in [('a--;', 'a -= 2;'), ('a = 2;', 'a = 1;'),
                         ('a += 16;', 'a += 15;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_fade_out_body', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_music_fade_limit_pause_and_track_volume_fail_the_gate(self):
        for old, new in [('if (a > 255)', 'if (a > 254)'),
                         ('level >> 2', 'level >> 3'), ('a |= b;', 'a &= b;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_fade_out_body', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_track_volume_pitch_clamp_bend_and_dirty_flags_fail_the_gate(self):
        for old, new in [('if ((int)b > 127)', 'if ((int)b > 126)'),
                         ('a = track->bend;', 'a = track->keyShift;'),
                         ('a = 0xFA;', 'a = 0xF0;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_track_update_volume_pitch', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_track_volume_pitch_scale_modulation_and_pan_fail_the_gate(self):
        for old, new in [('c = a >> 5;', 'c = a >> 4;'),
                         ('if (d != 1)', 'if (d != 2)'), ('a = 127;', 'a = 126;')]:
            with self.subTest(change=new):
                self.assert_reset_service_mutation_is_rejected('music_track_update_volume_pitch', old, new)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_pending_music_player_candidate_is_excluded_and_fails_full_gate(self):
        pending = json.loads((ROOT / 'config/candidates.usa.json').read_text())
        production = json.loads((ROOT / 'config/functions.usa.json').read_text())
        target = next(t for t in pending['functions'] if t['id'] == 'music_player_update')
        self.assertNotIn(target['id'], {t['id'] for t in production['functions']})
        self.assertEqual(target['source'], 'nonmatching/music_player_update.c')
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'pending music player'
            result = self.run_match('--function-map', ROOT / 'config/candidates.usa.json',
                                    '--target', target['id'], '--out-dir', out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / 'report.json').read_text())
            self.assertEqual(report['reference_size'], 616)
            self.assertFalse(report['equal'])
            self.assertGreater(report['different_bytes'], 0)
            self.assertFalse(report['assembly_postprocessing'])
            self.assertFalse(report['remaining_relocations'])

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_eeprom_capacity_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed EEPROM capacity.c"
            source = (ROOT / "src/eeprom_configure.c").read_text()
            self.assertEqual(source.count("value==64"), 1)
            candidate.write_text(source.replace("value==64", "value==32"))
            out = Path(temp) / "negative EEPROM"
            result = self.run_match("--target", "eeprom_configure", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)

    @unittest.skipUnless(READY, "requires user's USA ROM and local matching toolchain")
    def test_changed_save_header_sector_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "changed save header sector.c"
            source = (ROOT / "src/save_read_status.c").read_text()
            self.assertEqual(source.count("for(i=1;i<2;"), 1)
            candidate.write_text(source.replace("for(i=1;i<2;", "for(i=2;i<3;"))
            out = Path(temp) / "negative save header sector"
            result = self.run_match("--target", "save_read_status", "--source", candidate,
                                    "--out-dir", out)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["equal"])
            self.assertGreater(report["different_bytes"], 0)
            self.assertFalse(report["assembly_postprocessing"])
            self.assertFalse(report["remaining_relocations"])


if __name__ == "__main__":
    unittest.main()
