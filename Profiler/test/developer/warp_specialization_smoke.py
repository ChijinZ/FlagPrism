"""One fixed official ordinary kernel, no autotuning, profiling scopes or benchmark."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from triton.tools.tensor_descriptor import TensorDescriptor


def main(tutorial, output):
    output.mkdir(parents=True, exist_ok=False)
    from warp_specialization_matmul import matmul_kernel_tma
    kernel = matmul_kernel_tma
    m, n, k = 128, 128, 256
    bm, bn, bk = 128, 128, 64
    a = torch.linspace(-.25, .25, m * k, device='cuda').reshape(m, k).half()
    b = torch.linspace(.2, -.2, n * k, device='cuda').reshape(n, k).half()
    a_before, b_before = a.clone(), b.clone()
    c = torch.full((m + 1, n), -91., dtype=torch.float16, device='cuda')
    descriptors = [
        TensorDescriptor.from_tensor(value, shape)
        for value, shape in ((a, [bm, bk]), (b, [bn, bk]), (c[:m], [bm, bn]))
    ]
    binary = kernel[(1, )](*descriptors,
                           m,
                           n,
                           k,
                           BLOCK_SIZE_M=bm,
                           BLOCK_SIZE_N=bn,
                           BLOCK_SIZE_K=bk,
                           GROUP_SIZE_M=1,
                           FP8_OUTPUT=False,
                           WARP_SPECIALIZE=True,
                           num_warps=4,
                           num_stages=3)
    torch.cuda.synchronize()
    expected = (a.float().cpu() @ b.float().cpu().T).half()
    torch.testing.assert_close(c[:m].cpu(), expected, atol=.02, rtol=.02)
    assert torch.equal(a, a_before) and torch.equal(b, b_before)
    assert torch.equal(c[m].cpu(), torch.full((n, ), -91.,
                                              dtype=torch.float16))
    asm = binary.asm['ttgir']
    (output / 'actual.ttgir').write_text(asm)
    worker = 'ttg.warp_specialize' in asm and ('partition' in asm
                                               or 'warp_return' in asm)
    result = dict(status='pass',
                  math=True,
                  inputs_unchanged=True,
                  canary=True,
                  application_launch_calls=1,
                  binary=binary.hash,
                  actual_warp_specialize_worker_region=worker,
                  tutorial_sha256=hashlib.sha256(
                      tutorial.read_bytes()).hexdigest(),
                  actual_ttgir_sha256=hashlib.sha256(asm.encode()).hexdigest(),
                  config=dict(M=m,
                              N=n,
                              K=k,
                              BM=bm,
                              BN=bn,
                              BK=bk,
                              num_warps=4,
                              num_stages=3),
                  performance_benchmark=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tutorial', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    main(args.tutorial, args.output)
