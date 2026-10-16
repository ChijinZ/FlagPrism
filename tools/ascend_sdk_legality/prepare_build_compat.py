"""Apply the separately pinned build-only compatibility patch before compilation."""
from pathlib import Path
import hashlib

UTILS = "bishengir/lib/Dialect/Tensor/Transforms/PropagateReshape/Utils.cpp"
ORIGINAL_SHA = "a6185b7a3184c76e5e315837f112887dfa99bee814717a23efaf483623341c85"
PATCH_SHA = "4c6e07d319ed7b75c9a7d6ec718b8151c8abb0a5640c1e6eac360a6b17321d64"
FIXED_SHA = "08afbdcbf5549e27644454a03bea638d6a34c69b01bc67ab0394c6647ff29bca"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def apply(source, patch, run):
    if sha(patch) != PATCH_SHA or sha(source / UTILS) != ORIGINAL_SHA:
        raise RuntimeError("Build compatibility patch or original Utils source identity mismatch")
    run("build-compat-check", ["git", "apply", "--check", patch.resolve()], cwd=source, timeout=60)
    run("build-compat-apply", ["git", "apply", patch.resolve()], cwd=source, timeout=60)
    if sha(source / UTILS) != FIXED_SHA:
        raise RuntimeError("Build compatibility patch did not produce the frozen Utils source")
    return {"baseline_kind": "exact428 + explicit-template buildcompat, legality-unmodified",
            "build_compat_patch_sha256": PATCH_SHA, "utils_original_sha256": ORIGINAL_SHA,
            "utils_compat_sha256": FIXED_SHA}
