"""Developer regression: reject graph instrumentation and recover on two streams."""
import argparse
import json
from pathlib import Path
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler


@triton.jit
def elementwise(x, out, stream, n: tl.constexpr, block: tl.constexpr):
    i = tl.arange(0, block)
    value = tl.load(x + i, i < n, 0)
    tl.store(out + i, value * value + stream, i < n)


@triton.jit
def reduction(x, out, stream, n: tl.constexpr, block: tl.constexpr):
    i = tl.arange(0, block)
    value = tl.load(x + i, i < n, 0)
    result = tl.sum(tl.where(i < n, value * value + stream, 0), 0)
    tl.store(out, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', type=int, default=4)
    parser.add_argument('--cli', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.npu.set_device(args.device)
    cpu = torch.arange(257, dtype=torch.float32) / 32
    x = cpu.to(f'npu:{args.device}')
    streams = [torch.npu.Stream(device=args.device) for _ in range(2)]
    receipt = {
        'application_executions':
        1,
        'status':
        'running',
        'cases': [],
        'prewarm_collection':
        'profiled by outer CLI session'
        if args.cli else 'ordinary unprofiled prewarm'
    }

    def save():
        (args.output / 'result.json').write_text(json.dumps(receipt, indent=2))

    save()
    if not args.cli:
        rejected_output = args.output / 'start-inside-graph'
        try:
            with torch.npu.graph(torch.npu.NPUGraph(), stream=streams[0]):
                profiler.start(str(rejected_output),
                               backend='cann',
                               detail='auto')
        except RuntimeError as error:
            assert 'supports eager launches only' in str(error), error
            receipt['start_inside_graph_error'] = str(error)
        else:
            raise AssertionError(
                'automatic session started inside graph capture')
        assert not rejected_output.exists()
        assert not torch.npu.is_current_stream_capturing()
        save()

    for name, kernel in [('elementwise', elementwise),
                         ('reduction', reduction)]:
        expected = cpu * cpu + .75
        if name == 'reduction':
            expected = expected.sum().reshape(1)
        # Ordinary prewarm uses separate outputs; it cannot satisfy recovery.
        for stream in streams:
            with torch.npu.stream(stream):
                prewarm = torch.empty_like(expected, device=x.device)
                kernel[(1, )](x, prewarm, stream=.75, n=257, block=512)
        torch.npu.synchronize(args.device)
        session = None if args.cli else profiler.start(
            str(args.output / name), backend='cann', detail='auto')
        try:
            for stream in streams:
                storage = torch.full((expected.numel() + 32, ),
                                     -12345.,
                                     device=x.device)
                out = storage[16:-16]
                torch.npu.synchronize(args.device)
                try:
                    with torch.npu.graph(torch.npu.NPUGraph(), stream=stream):
                        kernel[(1, )](x, out, stream=.75, n=257, block=512)
                except RuntimeError as error:
                    assert 'supports eager launches only' in str(error), error
                    diagnostic = str(error)
                else:
                    raise AssertionError(
                        'detailed graph launch silently proceeded')
                assert not torch.npu.is_current_stream_capturing()
                assert torch.all(
                    out.cpu() == -12345.), 'rejected launch executed math'
                with torch.npu.stream(stream):
                    compiled = kernel[(1, )](x,
                                             out,
                                             stream=.75,
                                             n=257,
                                             block=512)
                torch.npu.synchronize(args.device)
                torch.testing.assert_close(out.cpu(), expected)
                torch.testing.assert_close(x.cpu(), cpu, atol=0, rtol=0)
                guards = storage.cpu()
                assert torch.all(guards[:16] == -12345.) and torch.all(
                    guards[-16:] == -12345.)
                receipt['cases'].append({
                    'kernel': name,
                    'stream_handle': int(stream.npu_stream),
                    'graph_error': diagnostic,
                    'rejected_output': 'unchanged sentinel',
                    'eager_math': 'passed',
                    'input': 'unchanged',
                    'canaries': 'passed',
                    'binary_id': compiled.hash
                })
                save()
        finally:
            if session is not None:
                profiler.finalize(session)
    receipt['status'] = 'passed'
    save()
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
