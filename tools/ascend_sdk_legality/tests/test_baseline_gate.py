#!/usr/bin/env python3
"""CPU-only positive/negative checks, including optimized Python execution."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

RECIPE = Path(__file__).resolve().parents[1]
REPLAY = None


class BaselineGate(unittest.TestCase):
    def run_comparator(self, data, optimized):
        with tempfile.TemporaryDirectory(prefix="sdk-gate-test-") as tmp:
            root = Path(tmp)
            actual = root / "actual.o"
            actual.write_bytes(data)
            result = subprocess.run([sys.executable, *(["-O"] if optimized else []),
                                     str(RECIPE / "compare_public_elf.py"),
                                     "--actual", str(actual), "--output", str(root / "result.json")],
                                    capture_output=True, text=True, timeout=30)
            return result.returncode

    def test_elf_mutations(self):
        original = (RECIPE / "tests/data/ordinary_reference.npubin").read_bytes()
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", original)
        # The public reference has section four .comment, outside PT_LOAD.
        comment_header = header[6] + 4 * header[11]
        section = struct.unpack_from("<IIQQQQIIQQ", original, comment_header)
        positive = bytearray(original)
        positive[section[4]] ^= 1
        variants = {"producer_only": (positive, True)}
        for name, offset in [("text", 176), ("load_header", header[5] + 8),
                             ("elf_flags", 48), ("symbol", 1840),
                             ("other_section_header", header[6] + header[11] + 32),
                             ("outside_section_padding", 1839)]:
            mutation = bytearray(positive)
            mutation[offset] ^= 1
            variants[name] = (mutation, False)
        allocated = bytearray(positive)
        struct.pack_into("<Q", allocated, comment_header + 8, section[2] | 2)
        variants["allocated_comment"] = (allocated, False)
        for name, size in [("overlap_comment", 201), ("beyond_file_comment", 10000)]:
            mutation = bytearray(positive)
            struct.pack_into("<Q", mutation, comment_header + 32, size)
            variants[name] = (mutation, False)
        for optimized in (False, True):
            for name, (data, accepted) in variants.items():
                with self.subTest(case=name, optimized=optimized):
                    self.assertEqual(self.run_comparator(data, optimized) == 0, accepted)

    def test_actual_replay_identities(self):
        if REPLAY is None:
            self.skipTest("pass --replay for actual compiler identity integration")
        replay = json.loads(REPLAY.read_text())
        self.assertIn(replay["state"], ("matched", "binary_mismatch"))
        # Matched replays use the real rebuild preflight, which requires byte
        # identity. Producer-only replays use their stricter derived-IR/ELF
        # validator; that validator deliberately rejects matched receipts.
        # Preserve the actual IR directory: the validator resolves it relative
        # to the receipt. Write fresh temporary receipts there, never overwrite.
        for optimized in (False, True):
            for key in (None, "compiler_sha256", "input_sha256", "binary_sha256", "reference_sha256",
                        "state", "byteequal"):
                changed = dict(replay)
                if key == "state":
                    changed[key] = "matched" if replay["state"] != "matched" else "binary_mismatch"
                elif key == "byteequal":
                    changed[key] = not replay["byteequal"]
                elif key:
                    changed[key] = "0" * 64
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix="gate-negative-",
                                                 dir=REPLAY.parent, delete=False) as stream:
                    json.dump(changed, stream)
                    receipt = Path(stream.name)
                with tempfile.TemporaryDirectory(prefix="sdk-gate-derived-") as tmp:
                    try:
                        command = [sys.executable, *(["-O"] if optimized else [])]
                        if replay["state"] == "matched":
                            command += ["-c", "import json,sys; from pathlib import Path; "
                                        "sys.path.insert(0, sys.argv[1]); "
                                        "from rebuild_fixed import validate_replay_identity; "
                                        "validate_replay_identity(json.loads(Path(sys.argv[2]).read_text()), "
                                        "Path(sys.argv[3]), require_matched=True)",
                                        str(RECIPE), str(receipt), replay["compiler"]]
                        else:
                            command += [str(RECIPE / "accept_public_baseline.py"),
                                        "--replay", str(receipt), "--output", str(Path(tmp) / "derived.json")]
                        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                        with self.subTest(key=key, optimized=optimized):
                            self.assertEqual(result.returncode == 0, key is None)
                    finally:
                        receipt.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    REPLAY = args.replay
    unittest.main(argv=[sys.argv[0]], verbosity=2)
