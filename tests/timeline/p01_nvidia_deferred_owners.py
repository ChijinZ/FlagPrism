"""Real two-stream owner/readback development test; not full timeline P01."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    import torch
    import triton
    import triton.language as tl
    import flagtree.debugger
    from triton.backends import backends
    from triton._C.libtriton import ir, nvidia, passes
    from triton.runtime._allocation import set_profile_allocator, NullAllocator
    from flagtree.profiler.native import compiler_binding
    from flagtree.profiler.mode import Default
    from flagtree.profiler.hooks.instrumentation import Instrumentation
    from flagtree.profiler import timeline_runtime, timeline_cuda_runtime
    from flagtree.profiler.timeline_nvidia import decode_timeline_ring
    for module in (timeline_runtime, timeline_cuda_runtime):
        require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()),
                'Runtime module fell back outside the installed wheel')
    torch.cuda.set_device(0)
    require(torch.cuda.get_device_capability() == (12, 0), 'Wrong booked device')
    torch.manual_seed(4317)
    binding = compiler_binding()
    mode = Default(buffer_size=32768)
    max_shared = triton.runtime.driver.active.utils.get_device_properties(0)['max_shared_mem']

    @triton.jit
    def recurrence(X, Y, Counter, K, N, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        lane = tl.arange(0, BLOCK)
        ix = pid * BLOCK + lane
        value = tl.load(X + ix, ix < N, 0)
        k = tl.load(K)
        for _ in range(k):
            value = value * 0.75 + 0.125
        tl.store(Y + ix, value, ix < N)
        prior = tl.load(Counter + pid + lane, lane == 0, 0)
        tl.store(Counter + pid + lane, prior + 1, lane == 0)

    def regions(pm):
        binding.add_automatic_proton_scopes(pm, 8, False, True)

    def lower(pm):
        binding.add_convert_proton_to_protongpu(
            pm, mode.metric_type, mode.sampling_strategy, mode.sampling_options,
            mode.granularity, mode.buffer_strategy, mode.buffer_type,
            mode.buffer_size, max_shared, 1, 128, True)
        passes.common.add_cse(pm)
        binding.add_allocate_proton_shared_memory(pm)

    def llvm(pm):
        binding.add_allocate_proton_global_scratch_buffer(pm)
        binding.add_convert_proton_nvidia_gpu_to_llvm(pm)

    pool = timeline_runtime.TimelineOwnerPool(
        timeline_cuda_runtime.CudaTimelineTransport(), max_owners=6,
        max_pending_bytes=6 * (2 * 32896 + 256), guard_bytes=256)
    actions, rows, calls = [], [], []

    def action(kind, **fields):
        actions.append(dict(kind=kind, host_monotonic_ns=time.monotonic_ns(), **fields))

    class Allocator:
        current = None

        def configure(self, compiled, plan):
            require(self.current is None, 'Previous submission still lacks completion handle')
            self.compiled, self.plan = compiled, plan

        def validate_launch(self, *, function, grid, scratch_size, alignment, num_ctas, stream=None):
            require(function == self.compiled.function, 'Binary/function admission mismatch')
            stream = int(torch.cuda.current_stream().cuda_stream)
            self.current = pool.prepare(self.plan, binary_id=self.compiled.hash,
                function=function, grid=grid, scratch_size=scratch_size,
                alignment=alignment, num_ctas=num_ctas, device=0, stream=stream)
            action('admitted', invocation_id=self.current)

        def __call__(self, size, alignment, stream):
            snapshot = pool.snapshot(self.current)
            require(size == snapshot['layout']['logical_request_bytes'] and
                    alignment == snapshot['layout']['alignment'] and
                    int(stream) == snapshot['stream'], 'Allocator actual ABI differs')
            buffer = pool.allocate(self.current)
            action('allocated', invocation_id=self.current, pointer=buffer.data_ptr())
            pool.mark_submitting(self.current)
            return buffer

    allocator = Allocator()
    backend = backends['nvidia'].compiler
    previous = backend.instrumentation
    collector = Instrumentation({'ttgpuir_complete': regions,
        'ttgpuir_to_llvmir': lower, 'llvmir_to_llvm': llvm})
    streams = [torch.cuda.Stream(), torch.cuda.Stream()]
    cases = []
    for i, k in enumerate((3, 7, 11, 3, 7, 11, 5)):
        grid = 3 if i % 2 == 0 else 5
        n = grid * 64 - 3
        xcpu = torch.rand(320)
        x = xcpu.cuda()
        y = torch.full((328,), -17.25, device='cuda')
        counter = torch.zeros(5, dtype=torch.int32, device='cuda')
        kd = torch.tensor(k, dtype=torch.int32, device='cuda')
        reference = xcpu[:n].clone()
        for _ in range(k):
            reference = reference * 0.75 + 0.125
        recurrence[(grid,)](x, y, counter, kd, n, 64, num_warps=4, instrumentation_mode='')
        calls.append(dict(case=i, kind='ordinary'))
        require(torch.allclose(y[:n].cpu(), reference, rtol=2e-6, atol=2e-6), 'Ordinary math failed')
        y.fill_(-17.25)
        counter.zero_()
        cases.append(dict(grid=grid, n=n, xcpu=xcpu, x=x, y=y, counter=counter,
                          kd=kd, reference=reference, stream=streams[i % 2]))
    inputs_ready = torch.cuda.Event()
    inputs_ready.record(torch.cuda.current_stream())
    for stream in streams:
        stream.wait_event(inputs_ready)
    token = str(mode) + ':timeline_timer=1:timeline_record=2:storage=1:deferred_owner=1'

    def submit(index):
        case = cases[index]
        with torch.cuda.stream(case['stream']):
            compiled = recurrence.run(case['x'], case['y'], case['counter'], case['kd'],
                case['n'], 64, grid=(case['grid'],), num_warps=4,
                instrumentation_mode=token, warmup=True)
            require(allocator.current is None, 'Compile-only unexpectedly allocated')
            path = args.output / ('case-' + str(index) + '.ttgir')
            path.write_text(compiled.asm['ttgir'])
            context = ir.context()
            ir.load_dialects(context)
            nvidia.load_dialects(context)
            binding.load_dialects(context)
            module = ir.parse_mlir_module(str(path), context)
            module.context = context
            plan = binding.get_automatic_proton_plan(module)
            plan['binary_id'] = compiled.hash
            allocator.configure(compiled, plan)
            action('launch_begin', case=index)
            recurrence.run(case['x'], case['y'], case['counter'], case['kd'],
                case['n'], 64, grid=(case['grid'],), num_warps=4,
                instrumentation_mode=token, warmup=False)
            identity = allocator.current
            pool.finish_submission(identity)
            allocator.current = None
            action('launch_return', case=index, invocation_id=identity)
            calls.append(dict(case=index, kind='instrumented'))
            rows.append(dict(case=index, invocation_id=identity, binary_id=compiled.hash,
                scope_ids=dict(binding.get_scope_id_names(module))))

    decoded_rows = []

    def read_row(row):
        identity = row['invocation_id']
        action('read_begin', invocation_id=identity)
        raw = pool.read(identity)
        snapshot = pool.snapshot(identity)
        decoded = decode_timeline_ring(raw,
            scratch_size=snapshot['layout']['scratch_size'], total_warps=4,
            selected_warps=(0, 1, 2, 3), slots=snapshot['layout']['slots'],
            scope_ids=frozenset(row['scope_ids']))
        require(decoded['complete'] and decoded['records'], 'Deferred record loss')
        require({event['program'] for event in decoded['records']} ==
                set(snapshot['layout']['programs']), 'Deferred invocation/program association changed')
        case = cases[row['case']]
        n = case['n']
        require(torch.allclose(case['y'][:n].cpu(), case['reference'], rtol=2e-6, atol=2e-6),
                'Deferred output math differs')
        require(torch.equal(case['y'][n:].cpu(), torch.full((328-n,), -17.25)),
                'Deferred output tail changed')
        require(case['counter'].cpu().tolist() == [1] * case['grid'] + [0] * (5-case['grid']),
                'Original program was replayed or skipped')
        require(torch.equal(case['x'].cpu(), case['xcpu']), 'Original input changed')
        stem = 'case-' + str(row['case'])
        (args.output / (stem + '.raw')).write_bytes(raw)
        (args.output / (stem + '.decoded.json')).write_text(json.dumps(decoded, indent=2)+'\n')
        decoded_rows.append(dict(case=row['case'], owner=snapshot,
            records=len(decoded['records']), raw_sha256=hashlib.sha256(raw).hexdigest(),
            raw_file=stem+'.raw', canary_verified=True))
        # Acknowledgement follows durable raw persistence, not the launch return.
        pool.release(identity)
        action('released', invocation_id=identity)

    try:
        backend.instrumentation = collector
        set_profile_allocator(allocator)
        for index in range(6):
            submit(index)
        require(len(pool.invocation_ids) == 6, 'Pending owners were drained during submission')
        before_reject = pool.pending_bytes
        try:
            submit(6)
        except RuntimeError as error:
            require('pending-owner budget' in str(error), 'Unexpected rejected launch failure')
            calls.append(dict(case=6, kind='rejected_before_allocation'))
        else:
            raise RuntimeError('Over-budget launch was submitted')
        require(pool.pending_bytes == before_reject and len(pool.invocation_ids) == 6,
                'Budget rejection changed in-flight owners')
        action('submissions_finished', pending_bytes=pool.pending_bytes)
        # Read in reverse order to expose accidental last-buffer association.
        for row in list(reversed(rows)):
            read_row(row)
        require(not pool.invocation_ids and pool.pending_bytes == 0, 'Owners were not released')
        require(cases[6]['counter'].cpu().tolist() == [0] * 5,
                'Rejected kernel produced device side effects')
        # A new legal launch works after the failed admission, without a replay.
        submit(6)
        read_row(rows[-1])
        require(len({row['binary_id'] for row in rows}) == 1, 'Runtime shape/grid recompiled binary')
        pointers = [a['pointer'] for a in actions if a['kind'] == 'allocated']
        require(len(set(pointers[:6])) == 6, 'In-flight owners shared allocations')
        pool.close()
        (args.output / 'result.json').write_text(json.dumps(dict(
            status='real_two_stream_deferred_owners_passed_not_full_P01',
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            runtime_modules={m.__name__: {'path':m.__file__,
                'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()}
                for m in (timeline_runtime, timeline_cuda_runtime)},
            calls=calls, actions=actions, captures=decoded_rows,
            limitations=['Development collector, no public timeline API/CLI integration yet',
                'No physical clock/epoch or final marker-order certificate',
                'Not a performance or engine-overlap claim', 'No Perfetto/independent qualification']), indent=2)+'\n')
    finally:
        backend.instrumentation = previous
        set_profile_allocator(NullAllocator())
        if allocator.current is not None:
            pool.abort(allocator.current)
            allocator.current = None
        for identity in pool.invocation_ids:
            # Safe failure cleanup waits only recorded owners, never frees a
            # pending writer merely because the application raised.
            state = pool.snapshot(identity)['state']
            if state in ('armed', 'submitting', 'quarantined', 'admitted'):
                pool.abort(identity)
                if identity not in pool.invocation_ids:
                    continue
            pool.read(identity)
            pool.release(identity)

if __name__ == '__main__':
    main()
