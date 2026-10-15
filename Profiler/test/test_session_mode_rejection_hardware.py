"""CUDA correctness regression: rejecting B must leave active profiler A usable.

Run explicitly with FLAGPRISM_RUN_CUDA_HARDWARE_TESTS=1 in an NVIDIA Docker.
This test measures correctness and record identity, never device performance.
"""
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("FLAGPRISM_RUN_CUDA_HARDWARE_TESTS") != "1",
    reason=
    "requires an explicitly reserved NVIDIA device and compiled profiler",
)


def test_conflicting_instrumentation_mode_keeps_existing_session_usable(
        tmp_path):
    torch = pytest.importorskip("torch")
    triton = pytest.importorskip("triton")
    tl = pytest.importorskip("triton.language")
    import flagtree.profiler as profiler
    from flagtree.profiler.native import runtime_binding

    @triton.jit
    def affine(X, Y, N: tl.constexpr, BLOCK: tl.constexpr):
        offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
        value = tl.load(X + offsets, offsets < N, other=0)
        transformed = value * 1.5 + 0.25
        tl.store(Y + offsets, transformed, offsets < N)

    x = torch.arange(257, device="cuda", dtype=torch.float32) / 512
    original = x.clone()
    y = torch.full((261, ), -91.0, device="cuda")
    expected = x * 1.5 + 0.25
    bundle = tmp_path / "active-session"
    session = profiler.start(str(bundle),
                             backend="instrumentation",
                             detail="auto")
    try:
        affine[(3, )](x, y, 257, 128)
        torch.cuda.synchronize()
        torch.testing.assert_close(y[:257], expected, rtol=0, atol=0)
        # Exercise the real public native session boundary. The unaccepted warp
        # option would poison A if singleton configuration changed pre-validation.
        with pytest.raises(RuntimeError, match="different mode"):
            runtime_binding().start(str(tmp_path / "rejected-session"),
                                    "shadow", "trace", "instrumentation",
                                    "cuda:sampling_options=999")
        affine[(3, )](x, y, 257, 128)
        torch.cuda.synchronize()
        torch.testing.assert_close(y[:257], expected, rtol=0, atol=0)
        assert torch.equal(x, original)
        assert bool(torch.all(y[257:] == -91.0).item())
    finally:
        profiler.finalize(session)
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest
    records = json.loads(
        (bundle / "ai" / "observations.json").read_text())["observations"]
    assert records
    assert len({record["capture_id"] for record in records}) == 2
    assert len({record["invocation_id"] for record in records}) == 2
    assert len({record["compiler_site"]["binary_id"]
                for record in records}) == 1
    assert all(record["association_status"] == "verified"
               for record in records)
    assert all(record["compiler_site"]["origin"]["source_capture"]
               for record in records)
    for name, metadata in manifest["files"].items():
        import hashlib
        payload = (bundle / name).read_bytes()
        assert len(payload) == metadata["bytes"]
        assert hashlib.sha256(payload).hexdigest() == metadata["sha256"]
