"""Development GPU qualification for unannotated source-linked automatic scopes.

Run with the installed FlagTree/FlagPrism environment. This is functional
qualification; it does not benchmark device latency or throughput.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import torch
import triton
import triton.language as tl
import flagtree.profiler as profiler


@triton.jit(do_not_specialize=['loops'])
def repeated_affine(X, Y, N, loops, BLOCK: tl.constexpr):
    index = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    value = tl.load(X + index, index < N, other=0)
    for step in range(loops):
        value = value * 0.5 + 0.25
    tl.store(Y + index, value, index < N)


@triton.jit
def centered_energy(X, Y, N, BLOCK: tl.constexpr):
    index = tl.arange(0, BLOCK)
    value = tl.load(X + index, index < N, other=0)
    centered = value - 0.125
    squared = tl.where(index < N, centered * centered, 0)
    energy = tl.sum(squared, axis=0)
    tl.store(Y, energy)


def validate_bundle(base):
    exported = json.loads((base / 'ai/observations.json').read_text())
    assert len(exported['captures']) == 1, exported.keys()
    capture = exported['captures'][0]
    plan = capture['automatic_plan']
    assert plan['schema_version'] == 2
    assert plan['binary_id'] == capture['binary_id']
    assert plan['compiler_ir_sha256'] == capture['compiler_ir_sha256']
    assert ':automatic=2:control_policy=2:source_metadata=1:' in capture[
        'compiler_metadata']['instrumentation_mode']
    inventory = plan['inventory']
    assert len(inventory) == plan['proton.automatic_candidates']
    assert sum(row['selected']
               for row in inventory) == plan['proton.automatic_selected']
    assert any(row['candidate_class'] == 'source_statement'
               for row in inventory)
    names = dict(capture['scope_id_names'])
    for row in inventory:
        assert row['operation'] and row['location'] and row['selection_reason']
        if row['selected']:
            assert names[row['scope_id']] == row['selected_scope_name']
            assert row['location'] == capture['scope_id_origins'][str(
                row['scope_id'])]['entry'][0]
        else:
            assert row['scope_id'] is None and row[
                'selected_scope_name'] is None
    decoded = capture['decoded']
    assert decoded['dropped_records'] == 0, decoded['losses']
    assert not decoded['unpaired_records'], decoded['unpaired_records']
    records = exported['observations']
    assert len({record['site'] for record in records}) >= 2, records
    assert all(
        record['invocation_id'] and record['association_status'] == 'verified'
        for record in records)
    assert all(
        record['compiler_site']['kind'] == 'automatic_compiler_operation'
        and record['compiler_site']['origin']['operation']
        and record['compiler_site']['origin']['source_capture']
        and record['compiler_site']['origin']['status'] != 'unknown'
        for record in records), records
    fine = json.loads((base / 'ai/fine_grained.json').read_text())
    assert len(fine['records']) == len(records), fine
    assert all(row['source_locations'] and row['operation']
               and row['association_status'] == 'verified'
               for row in fine['records']), fine
    assert (base / 'report/fine_grained.html').is_file()
    assert (base / 'ai/observation_plan.json').is_file()
    return records, capture


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    x = torch.linspace(-1, 1, 137, device='cuda')
    y = torch.empty_like(x)
    binaries = set()
    summaries = []
    for loops in (0, 1, 3, 7):
        baseline_started = time.monotonic()
        repeated_affine[(1, )](x,
                               y,
                               x.numel(),
                               loops,
                               256,
                               num_warps=4,
                               num_stages=1)
        baseline_compile_launch_seconds = time.monotonic() - baseline_started
        expected = x.cpu()
        for _ in range(loops):
            expected = expected * 0.5 + 0.25
        torch.testing.assert_close(y.cpu(), expected)
        base = output / f'loop-{loops}'
        session = profiler.start(str(base), detail='auto')
        compile_started = time.monotonic()
        compiled = repeated_affine[(1, )](x,
                                          y,
                                          x.numel(),
                                          loops,
                                          256,
                                          num_warps=4,
                                          num_stages=1)
        compile_launch_seconds = time.monotonic() - compile_started
        binaries.add(compiled.hash)
        export_started = time.monotonic()
        profiler.finalize(session)
        export_seconds = time.monotonic() - export_started
        assert compile_launch_seconds <= min(
            300, max(120, 3 * baseline_compile_launch_seconds))
        assert export_seconds <= 60
        torch.testing.assert_close(y.cpu(), expected)
        records, capture = validate_bundle(base)
        repeated = [
            record for record in records
            if record['compiler_site']['origin']['operation'] == 'arith.mulf'
        ]
        assert len(repeated) == loops, (loops, repeated, records)
        summaries.append({
            'loops': loops,
            'binary_id': compiled.hash,
            'observations': len(records),
            'repeated_multiply_visits': len(repeated),
            'automatic_plan': capture['automatic_plan'],
            'baseline_compile_launch_wall_seconds':
            baseline_compile_launch_seconds,
            'instrumented_compile_launch_wall_seconds': compile_launch_seconds,
            'export_wall_seconds': export_seconds
        })
    assert len(binaries) == 1, binaries
    z = torch.empty((), device='cuda')
    centered_energy[(1, )](x, z, x.numel(), 256, num_warps=4, num_stages=1)
    expected = ((x.cpu() - 0.125)**2).sum()
    torch.testing.assert_close(z.cpu(), expected)
    base = output / 'reduction'
    session = profiler.start(str(base), detail='auto')
    centered_energy[(1, )](x, z, x.numel(), 256, num_warps=4, num_stages=1)
    profiler.finalize(session)
    torch.testing.assert_close(z.cpu(), expected)
    records, capture = validate_bundle(base)
    assert any(record['compiler_site']['origin']['operation'] == 'tt.reduce'
               for record in records), records
    result = {
        'source_sha256': source_hash,
        'pid': os.getpid(),
        'loop_cases': summaries,
        'reduction_observations': len(records),
        'torch': torch.__version__,
        'triton': triton.__version__,
        'device': torch.cuda.get_device_name(0)
    }
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
