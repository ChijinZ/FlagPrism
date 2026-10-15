"""Unannotated development coverage for branch, matrix, tails and specializations."""
import json
from pathlib import Path
import sys
import torch
import triton
import triton.language as tl
import flagtree.profiler as profiler
from automatic_hardware import validate_bundle


@triton.jit(do_not_specialize=['choice'])
def selected_expression(X, Y, N, choice, B: tl.constexpr):
    i = tl.program_id(0) * B + tl.arange(0, B)
    x = tl.load(X + i, i < N, other=0)
    if choice > 0:
        y = x * x
    else:
        y = tl.abs(x)
    tl.store(Y + i, y + 0.5, i < N)


@triton.jit
def tiled_product(A, B, C, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                  T: tl.constexpr):
    r = tl.arange(0, T)
    a = tl.load(A + r[:, None] * K + r[None, :],
                (r[:, None] < M) & (r[None, :] < K),
                other=0)
    b = tl.load(B + r[:, None] * N + r[None, :],
                (r[:, None] < K) & (r[None, :] < N),
                other=0)
    c = tl.dot(a, b, input_precision='ieee')
    tl.store(C + r[:, None] * N + r[None, :], c,
             (r[:, None] < M) & (r[None, :] < N))


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for n in (129, 256):
        x = torch.linspace(-2, 2, n, device='cuda')
        original = x.clone()
        for block, warps in ((256, 4), (512, 8)):
            binaries = set()
            for choice in (0, 2):
                y = torch.full((n + 7, ), -99., device='cuda')
                expected = (x.cpu().abs() if choice == 0 else x.cpu()**2) + 0.5
                selected_expression[(1, )](x,
                                           y,
                                           n,
                                           choice,
                                           block,
                                           num_warps=warps,
                                           num_stages=1)
                torch.testing.assert_close(y[:n].cpu(), expected)
                base = output / f'branch-{n}-{block}-{choice}'
                session = profiler.start(str(base), detail='auto')
                compiled = selected_expression[(1, )](x,
                                                      y,
                                                      n,
                                                      choice,
                                                      block,
                                                      num_warps=warps,
                                                      num_stages=1)
                profiler.finalize(session)
                binaries.add(compiled.hash)
                torch.testing.assert_close(y[:n].cpu(), expected)
                assert torch.equal(y[n:].cpu(), torch.full((7, ), -99.))
                assert torch.equal(x, original)
                records, capture = validate_bundle(base)
                observed = {
                    r['compiler_site']['origin']['operation']
                    for r in records
                }
                assert ('arith.mulf' in observed) == (choice > 0), observed
                assert ('math.absf' in observed) == (choice == 0), observed
                inventory = {int(k) for k in capture['scope_id_origins']}
                assert inventory - {r['site']
                                    for r in records}, (inventory, records)
                rows.append({
                    'kind': 'branch',
                    'n': n,
                    'block': block,
                    'warps': warps,
                    'choice': choice,
                    'binary_id': compiled.hash,
                    'observations': len(records)
                })
            assert len(binaries) == 1, binaries
    for shape in ((13, 15, 11), (16, 16, 16)):
        m, n, k = shape
        a = torch.randn((m, k), device='cuda')
        b = torch.randn((k, n), device='cuda')
        original_a, original_b = a.clone(), b.clone()
        expected = a.cpu() @ b.cpu()
        for warps in (4, 8):
            c = torch.empty((m, n), device='cuda')
            tiled_product[(1, )](a,
                                 b,
                                 c,
                                 m,
                                 n,
                                 k,
                                 16,
                                 num_warps=warps,
                                 num_stages=1)
            torch.testing.assert_close(c.cpu(), expected)
            base = output / f'matrix-{m}-{n}-{k}-{warps}'
            session = profiler.start(str(base), detail='auto')
            compiled = tiled_product[(1, )](a,
                                            b,
                                            c,
                                            m,
                                            n,
                                            k,
                                            16,
                                            num_warps=warps,
                                            num_stages=1)
            profiler.finalize(session)
            torch.testing.assert_close(c.cpu(), expected)
            assert torch.equal(a, original_a) and torch.equal(b, original_b)
            records, capture = validate_bundle(base)
            inventory = capture['automatic_plan']['inventory']
            assert any(not row['selected'] and row['scope_id'] is None
                       for row in inventory)
            assert any(
                row['selected'] and row['candidate_ordinal'] != row['scope_id']
                for row in inventory)
            assert any(r['compiler_site']['origin']['operation'] == 'tt.dot'
                       for r in records), records
            rows.append({
                'kind':
                'matrix',
                'shape':
                shape,
                'warps':
                warps,
                'binary_id':
                compiled.hash,
                'observations':
                len(records),
                'operations':
                sorted({
                    r['compiler_site']['origin']['operation']
                    for r in records
                })
            })
    (output / 'result.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2), flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
