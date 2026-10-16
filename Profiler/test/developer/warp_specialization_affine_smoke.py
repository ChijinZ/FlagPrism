"""Second ordinary TMA pipeline math, runtime K2/5 and one device call witness."""
from pathlib import Path
import argparse, json
import torch
from triton.tools.tensor_descriptor import TensorDescriptor
from warp_specialization_affine import affine_matmul_kernel


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for k in (128, 320):
        m, n, bm, bn, bk = 128, 96, 128, 128, 64
        a = torch.linspace(-.25, .25, m * k, device='cuda').reshape(m,
                                                                    k).half()
        b = torch.linspace(.2, -.2, n * k, device='cuda').reshape(n, k).half()
        bias = torch.linspace(-.4, .4, n, device='cuda').half()
        originals = [x.clone() for x in (a, b, bias)]
        c = torch.full((m + 1, n), -91., dtype=torch.float16, device='cuda')
        calls = torch.zeros((), dtype=torch.int32, device='cuda')
        descriptors = [
            TensorDescriptor.from_tensor(value, shape)
            for value, shape in ((a, [bm, bk]), (b, [bn, bk]), (c[:m],
                                                                [bm, bn]))
        ]
        binary = affine_matmul_kernel[(1, )](*descriptors,
                                             bias,
                                             calls,
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
        expected = (a.float().cpu() @ b.float().cpu().T +
                    bias.float().cpu()[None, :]).clamp_min(0).half()
        torch.testing.assert_close(c[:m].cpu(), expected, atol=.03, rtol=.03)
        assert all(torch.equal(x, y) for x, y in zip((a, b, bias), originals))
        assert torch.equal(c[m].cpu(),
                           torch.full((n, ), -91., dtype=torch.float16))
        assert calls.item() == 1
        asm = binary.asm['ttgir']
        (output / f'K{k}.ttgir').write_text(asm)
        worker = 'ttg.warp_specialize' in asm and 'partition1' in asm
        assert worker
        results.append(
            dict(k=k,
                 k_tiles=k // bk,
                 binary=binary.hash,
                 math=True,
                 canary=True,
                 inputs_unchanged=True,
                 device_calls=1,
                 actual_worker_region=worker))
    assert results[0]['binary'] == results[1]['binary']
    (output / 'summary.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('output', type=Path)
    main(p.parse_args().output)
