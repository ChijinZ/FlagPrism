#!/usr/bin/env python3
"""Exercise the actual clean-build compatibility entry with public source only."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prepare_build_compat import apply, sha, UTILS, FIXED_SHA
PATCH = ROOT.parents[1] / "integration/patches/ascend/sdk-build-explicit-collapse-instantiation.patch"


class PrepareCompatibility(unittest.TestCase):
    def test_preparation_and_rejections(self):
        with tempfile.TemporaryDirectory(prefix="sdk-compat-test-") as tmp:
            source = Path(tmp)
            target = source / UTILS
            target.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / "tests/source_fixture/Utils.cpp", target)
            commands = []

            def run(label, argv, cwd, timeout):
                commands.append(label)
                subprocess.run(list(map(str, argv)), cwd=cwd, timeout=timeout,
                               check=True, capture_output=True)

            changed_patch = source / "wrong.patch"
            changed_patch.write_bytes(PATCH.read_bytes() + b"\n")
            with self.assertRaises(RuntimeError):
                apply(source, changed_patch, run)
            original = target.read_bytes()
            target.write_bytes(original + b"\n")
            with self.assertRaises(RuntimeError):
                apply(source, PATCH, run)
            target.write_bytes(original)
            result = apply(source, PATCH, run)
            self.assertEqual(sha(target), FIXED_SHA)
            self.assertEqual(result["utils_compat_sha256"], FIXED_SHA)
            self.assertEqual(commands, ["build-compat-check", "build-compat-apply"])
            with self.assertRaises(RuntimeError):
                apply(source, PATCH, run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
