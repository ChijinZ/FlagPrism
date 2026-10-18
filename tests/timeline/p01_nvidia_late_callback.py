"""Installed parent callback compilation/cache test; does not launch kernels."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
import triton
import triton.language as tl
from triton.backends.nvidia.compiler import CUDABackend
from flagtree.profiler.hooks.instrumentation import Instrumentation
from flagtree.profiler.timeline_nvidia_late_compile import LateLLVMTransform
import flagtree.profiler.timeline_nvidia_late_compile as implementation


@triton.jit
def square_bias(X, Y, N: tl.constexpr, B: tl.constexpr):
    offset = tl.program_id(0) * B + tl.arange(0, B)
    value = tl.load(X + offset, offset < N, 0.0)
    output = value * value + 0.25
    tl.store(Y + offset, output, offset < N)


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    need(CUDABackend.optimized_llvm_transform_version == 1,
         'Parent compiler lacks optimized LLVM callback')
    tool = Path(implementation.__file__).parent / '_bin/late-timeline'
    transform = LateLLVMTransform(tool, a.output / 'attempts')
    torch.cuda.set_device(0)
    x = torch.empty(1024, device='cuda')
    y = torch.empty_like(x)
    ordinary = square_bias.warmup(x, y, 1024, 512, grid=(2, ), num_warps=4)
    previous = CUDABackend.instrumentation
    try:
        CUDABackend.instrumentation = Instrumentation(
            {'optimized_llvm': transform})
        mode = 'late-callback-test:' + hashlib.sha256(
            json.dumps(transform.cache_identity,
                       sort_keys=True).encode()).hexdigest()
        profiled = square_bias.warmup(x,
                                      y,
                                      1024,
                                      512,
                                      grid=(2, ),
                                      num_warps=4,
                                      instrumentation_mode=mode)
        manifest = profiled.metadata.flagprism_late_manifest
        need(
            profiled.metadata.profile_scratch_size == manifest['segment_words']
            * 8, 'Parent overwrote callback scratch size')
        need(profiled.metadata.profile_scratch_align == 8,
             'Parent overwrote callback scratch alignment')
        need(
            hashlib.sha256(profiled.asm['llir'].encode()).hexdigest() ==
            manifest['compiler_binding']['output_sha256'],
            'Returned IR does not match retained native output')
        attempts = sorted(str(p) for p in (a.output / 'attempts').iterdir())
        need(len(attempts) == 1, 'Expected one actual cold transform')
        warm = square_bias.warmup(x,
                                  y,
                                  1024,
                                  512,
                                  grid=(2, ),
                                  num_warps=4,
                                  instrumentation_mode=mode)
        need(
            warm.hash == profiled.hash
            and sorted(str(p)
                       for p in (a.output / 'attempts').iterdir()) == attempts,
            'Warm compilation did not reuse bound cached variant')
        need(
            profiled.hash != ordinary.hash
            and ordinary.metadata.profile_scratch_size == 0,
            'Instrumented and ordinary cache entries were mixed')
    finally:
        CUDABackend.instrumentation = previous
    # The shared manager's absent callback remains transparent; malformed
    # callbacks fail before any LLVM translation or launch.
    need(
        Instrumentation({}).transform_optimized_llvm('original',
                                                     {}) == 'original',
        'Existing compiler manager behavior changed')
    for bad in (None, '', b'not text'):
        try:
            Instrumentation({
                'optimized_llvm': lambda *args: bad
            }).transform_optimized_llvm('original', {})
        except RuntimeError:
            pass
        else:
            raise RuntimeError('Malformed callback return was accepted')
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'installed_parent_late_callback_and_cache_passed_no_kernel_launch',
            ordinary_hash=ordinary.hash,
            profiled_hash=profiled.hash,
            manifest=manifest,
            cache_identity=transform.cache_identity,
            device=str(torch.cuda.get_device_properties(0))),
                   indent=2))


if __name__ == '__main__':
    main()
