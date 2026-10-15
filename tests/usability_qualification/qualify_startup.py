"""Q1 launch-only adapter to unchanged Q0 qualification controller.

The adapter changes the user startup script in the EXTERNAL command only.
It does not import, patch or call any profiler API. Original Q0 files/manifests
are retained byte-for-byte; numerical kernels and all CLI arguments stay intact.
"""
import hashlib
import json
from pathlib import Path

import qualify


def main():
    here = Path(__file__).resolve().parent
    manifest = json.loads((here / "startup-manifest-Q1.json").read_text())
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((here / name).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((here / "manifest.json").read_bytes()).hexdigest() == manifest["Q0_manifest_sha256"]
    original_execute = qualify.execute

    def launch_with_sdk_startup(command, dest, env, timeout):
        ordinary_script = str(here / "workload.py")
        assert command.count(ordinary_script) == 1
        actual_command = [str(here / "ascend_startup.py") if part == ordinary_script else part
                          for part in command]
        # Both baseline and later default CLI receive this same ordinary startup.
        return original_execute(actual_command, dest, env, timeout)

    qualify.execute = launch_with_sdk_startup
    qualify.main()


if __name__ == "__main__":
    main()
