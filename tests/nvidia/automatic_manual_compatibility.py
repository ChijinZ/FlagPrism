"""Explicit advanced scopes remain compatible in a fresh installed package."""
import json
from pathlib import Path
import sys
import torch
import triton
import triton.language as tl
import flagtree.profiler as profiler
from flagtree.profiler import language as pl

pl.enable_semantic('triton')


@triton.jit(do_not_specialize=['repeats'])
def explicit_loop(X, Y, repeats, B: tl.constexpr):
    i = tl.arange(0, B)
    x = tl.load(X + i)
    for iteration in range(repeats):
        pl.enter_scope('advanced_source_interval')
        x = x + 0.25
        pl.exit_scope('advanced_source_interval')
    tl.store(Y + i, x)


output = Path(sys.argv[1])
x = torch.linspace(-1, 1, 128, device='cuda')
y = torch.empty_like(x)
session = profiler.start(str(output),
                         backend='instrumentation',
                         hook='instrumentation',
                         mode=profiler.mode.Default(
                             sampling_strategy='selective',
                             sampling_options='0',
                             granularity='warp',
                             buffer_size=1024))
explicit_loop[(1, )](x, y, 4, 128, num_warps=4, num_stages=1)
profiler.finalize(session)
torch.testing.assert_close(y.cpu(), x.cpu() + 1)
exported = json.loads((output / 'ai/observations.json').read_text())
assert len(exported['observations']) == 4
assert all(record['scope_name'] == 'advanced_source_interval'
           and record['compiler_site']['kind'] == 'explicit_proton_scope'
           for record in exported['observations'])
assert exported['captures'][0]['decoded']['dropped_records'] == 0
print('PASS INSTALLED_MANUAL_SCOPE_COMPATIBILITY', flush=True)
