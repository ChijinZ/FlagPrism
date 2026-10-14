"""GCU final-artifact mapping oracle, including an RMSNorm heldout kernel.

Run inside the Enflame Docker with FLAGPRISM_TEST_ENFLAME=1 and selected GCU.
The source has no Study names/shapes; CPU math and compiler SSA are the oracles.
"""
import os
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("FLAGPRISM_TEST_ENFLAME") != "1",
                                reason="requires selected real Enflame hardware")


@pytest.mark.parametrize("n,block,work_items", [(251, 256, 1), (777, 1024, 4), (1031, 2048, 8)])
def test_rms_final_artifact_mapping(n, block, work_items, tmp_path):
    import json
    import torch
    import torch_gcu  # noqa: F401
    import triton
    import triton.language as tl
    from flagtree.profiler.execution_enflame import build_execution_mapping

    @triton.jit
    def reserved_validation(X, Y, N: tl.constexpr, B: tl.constexpr):
        row = tl.program_id(0)
        col = tl.arange(0, B)
        x = tl.load(X + row * N + col, col < N, 0)
        inv = tl.rsqrt(tl.sum(x * x, 0) / N + 1.e-5)
        tl.store(Y + row * N + col, x * inv, col < N)

    cpu = torch.arange(3 * n, dtype=torch.float32, device="cpu").reshape(3, n) / (3*n)
    x = cpu.to("gcu")
    y = torch.empty_like(x)
    kernel = reserved_validation[(3,)](x, y, n, block, num_warps=work_items)
    torch.gcu.synchronize()
    expected = cpu * torch.rsqrt((cpu * cpu).mean(dim=1, keepdim=True) + 1.e-5)
    torch.testing.assert_close(y.cpu(), expected, rtol=2.e-5, atol=2.e-5)
    metadata = kernel.metadata._asdict()
    metadata.pop("target", None)
    mapping = build_execution_mapping(kernel.asm, metadata, binary_id=kernel.hash)
    (tmp_path / "mapping.json").write_text(json.dumps(mapping, default=str, indent=2))
    assert mapping["work_item_count"] == work_items
    assert mapping["status"] == "partial"
    assert not mapping["source_associations"]
    assert mapping["source_origin_associations"]
    assert all(not row["exclusive_cost"] for row in mapping["source_origin_associations"])
    assert all(row["identity_kind"] == "ttir_operation_with_debug_origin"
               for row in mapping["origin_source_operations"])
    assert 'loc(' in kernel.asm['gcuir']
    ownership = "single_work_item" if work_items == 1 else "symbolic"
    assert any(site["ownership_status"] == ownership for site in mapping["sites"])
    if work_items > 1:
        assert any(site["kind"] == "partial_exchange_storage" for site in mapping["sites"])
        assert any(site["kind"] == "barrier" for site in mapping["sites"])
