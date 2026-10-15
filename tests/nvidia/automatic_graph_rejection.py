"""Detailed automatic/manual graph capture rejects before collection and recovers."""
import json
from pathlib import Path
import sys
import torch
import triton
import triton.language as tl
import flagtree.profiler as profiler
from flagtree.profiler import language as pl
from flagtree.profiler.hooks.instrumentation import InstrumentationHook
from flagtree.profiler.observations import ObservationRequest

pl.enable_semantic('triton')


@triton.jit
def automatic(X, Y, B: tl.constexpr):
    i = tl.arange(0, B)
    x = tl.load(X + i)
    tl.store(Y + i, x * x + 1)


@triton.jit
def manual(X, Y, B: tl.constexpr):
    i = tl.arange(0, B)
    x = tl.load(X + i)
    pl.enter_scope('manual_interval')
    y = x * x + 1
    pl.exit_scope('manual_interval')
    tl.store(Y + i, y)


output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
x = torch.linspace(-1, 1, 128, device='cuda')
y = torch.empty_like(x)
stream = torch.cuda.Stream()
stream.wait_stream(torch.cuda.current_stream())
for kind, kernel in [('automatic', automatic), ('manual', manual)]:
    base = output / kind
    if kind == 'automatic':
        session = profiler.start(str(base), detail='auto')
    else:
        session = profiler.start(str(base),
                                 backend='instrumentation',
                                 hook='instrumentation',
                                 observation_request=ObservationRequest())
    graph = torch.cuda.CUDAGraph()
    try:
        with torch.cuda.graph(graph, stream=stream):
            kernel[(1, )](x, y, 128, num_warps=4, num_stages=1)
    except RuntimeError as error:
        assert 'eager launches only' in str(
            error) and 'native-only CUDA graph' in str(error), error
    else:
        raise AssertionError('Detailed graph capture silently proceeded')
    assert not torch.cuda.is_current_stream_capturing()
    assert InstrumentationHook.active_count == 1
    kernel[(1, )](x, y, 128, num_warps=4, num_stages=1)
    profiler.finalize(session)
    assert InstrumentationHook.active_count == 0
    torch.testing.assert_close(y.cpu(), x.cpu() * x.cpu() + 1)
    records = json.loads((base / 'ai/observations.json').read_text())
    assert len(records['captures']) == 1
    assert records['observations'] and all(
        r['association_status'] == 'verified' for r in records['observations'])
    print('PASS_GRAPH_REJECTION_AND_EAGER_RECOVERY', kind, flush=True)
