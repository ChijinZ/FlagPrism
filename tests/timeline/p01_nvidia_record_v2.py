"""Real ordinary math through automatic full-width record lowering.

Development mechanism test, not the public timeline interface or complete P01.
No kernel annotations. The test collector explicitly owns each allocation and
waits for its completion; it does not claim concurrent runtime qualification.
"""
import argparse
import hashlib
import json
from math import prod
from pathlib import Path
import sys
import uuid


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    import torch
    import triton
    import triton.language as tl
    import flagtree.debugger  # Registers source statement metadata, no device work.
    from triton.backends import backends
    from triton._C.libtriton import ir, nvidia, passes
    from triton.runtime._allocation import set_profile_allocator, NullAllocator
    from flagtree.profiler.native import compiler_binding
    from flagtree.profiler.hooks.instrumentation import Instrumentation
    from flagtree.profiler.mode import Default

    from flagtree.profiler import timeline_nvidia as decoder
    module_path = Path(decoder.__file__).resolve()
    require(module_path.is_relative_to(Path(sys.prefix).resolve()),
            'Decoder fell back outside the actual wheel installation')
    from flagtree.profiler.timeline_nvidia_async import derive_cp_async_facts
    capture_namespace = uuid.uuid4().hex
    binding = compiler_binding()
    require(binding.TIMELINE_RECORD_VERSION == 2 and binding.TIMELINE_STORAGE_VERSION == 1,
            'Wrong installed native record/storage ABI')
    from flagtree.profiler.timeline_storage import plan_compact_storage
    torch.cuda.set_device(0)
    require(torch.cuda.get_device_capability() == (12, 0), 'Wrong booked device')
    torch.manual_seed(9217)

    @triton.jit
    def recurrence(X, Y, K, State, N: tl.constexpr, BLOCK: tl.constexpr):
        pid = tl.program_id(0)
        ix = pid * BLOCK + tl.arange(0, BLOCK)
        value = tl.load(X + ix, ix < N, 0)
        k = tl.load(K)
        for _ in range(k):
            value = value * 0.75 + 0.125
        tl.store(Y + ix, value, ix < N)
        lane = tl.arange(0, BLOCK)
        prior = tl.load(State + pid + lane, lane == 0, 0)
        tl.store(State + pid + lane, prior + 1, lane == 0)

    @triton.jit
    def gemm(A, B, C, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
             BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
        r = tl.program_id(0) * BM + tl.arange(0, BM)
        c = tl.program_id(1) * BN + tl.arange(0, BN)
        kk = tl.arange(0, BK)
        accum = tl.full((BM, BN), 0, tl.float32)
        for tile in range(tl.cdiv(K, BK)):
            ks = tile * BK + kk
            av = tl.load(A + r[:, None] * K + ks[None, :],
                         (r[:, None] < M) & (ks[None, :] < K), 0)
            bv = tl.load(B + ks[:, None] * N + c[None, :],
                         (ks[:, None] < K) & (c[None, :] < N), 0)
            accum += tl.dot(av, bv)
        tl.store(C + r[:, None] * N + c[None, :], accum,
                 (r[:, None] < M) & (c[None, :] < N))

    @triton.jit
    def grid_map(X, Y, State, N, BLOCK: tl.constexpr):
        pid = (tl.program_id(0) + tl.program_id(1) * tl.num_programs(0) +
               tl.program_id(2) * tl.num_programs(0) * tl.num_programs(1))
        lane = tl.arange(0, BLOCK)
        ix = pid * BLOCK + lane
        value = tl.load(X + ix, ix < N, 0)
        value = value * 0.625 + 0.25
        tl.store(Y + ix, value, ix < N)
        prior = tl.load(State + pid + lane, lane == 0, 0)
        tl.store(State + pid + lane, prior + 1, lane == 0)

    allocations = []

    class Allocator:
        def __init__(self, plan, compiled):
            self.compiled_plan, self.compiled = plan, compiled

        def validate_launch(self, *, function, grid, scratch_size, alignment, num_ctas):
            require(num_ctas == 1, 'This mechanism registration uses noncluster CTAs')
            require(function == self.compiled.function,
                    'Allocator plan is not bound to the actual loaded binary')
            layout = plan_compact_storage(self.compiled_plan, grid=grid,
                scratch_size=scratch_size, alignment=alignment, num_ctas=num_ctas)
            self.plan = dict(function=function, grid=list(grid), stride=scratch_size,
                             alignment=alignment, size=prod(grid) * scratch_size,
                             layout=layout)

        def __call__(self, size, alignment, stream):
            require(size == self.plan['size'] and alignment == self.plan['alignment'],
                    'Actual allocation contradicts the prelaunch ABI')
            raw_bytes = self.plan['layout']['raw_bytes']
            require(0 < raw_bytes <= 8388608, 'Mechanism scratch exceeded raw budget')
            target_stream = torch.cuda.current_stream() if stream is None else torch.cuda.ExternalStream(stream)
            with torch.cuda.stream(target_stream):
                allocation = torch.full((raw_bytes + 256,), 165, dtype=torch.uint8, device='cuda')
                buffer = allocation[:raw_bytes]
                buffer.zero_()
            allocations.append(dict(self.plan, buffer=buffer, allocation=allocation,
                                    stream=target_stream))
            return buffer

    mode = Default(buffer_size=32768)
    max_shared = triton.runtime.driver.active.utils.get_device_properties(0)['max_shared_mem']
    selected = (0,)

    def regions(pm):
        binding.add_automatic_proton_scopes(pm, 8, False, True)
        if selected is not None:
            binding.add_select_proton_programs(pm, list(selected))

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

    backend = backends['nvidia'].compiler
    previous = backend.instrumentation
    collector = Instrumentation({'ttgpuir_complete': regions,
                                 'ttgpuir_to_llvmir': lower, 'llvmir_to_llvm': llvm})
    rows = []
    calls = []

    def save(name, value):
        (a.output / name).write_text(json.dumps(value, indent=2) + '\n')

    def collect(name, launch, programs):
        nonlocal selected
        selected = programs
        backend.instrumentation = collector
        count = len(allocations)
        selection_key = 'runtime_first_last' if selected is None else ','.join(map(str, selected))
        token = str(mode) + ':timeline_timer=1:timeline_record=2:storage=1:selected=' + selection_key
        # Compile-only discovery is not an extra application/device invocation.
        compiled = launch(token, warmup=True)
        require(len(allocations) == count, 'Compile-only discovery allocated device records')
        context = ir.context()
        ir.load_dialects(context)
        nvidia.load_dialects(context)
        binding.load_dialects(context)
        prelaunch_ir = a.output / (name + '.prelaunch.ttgir')
        prelaunch_ir.write_text(compiled.asm['ttgir'])
        module = ir.parse_mlir_module(str(prelaunch_ir), context)
        module.context = context
        compiled_plan = binding.get_automatic_proton_plan(module)
        require(compiled_plan.get('timeline_storage_version') == 1,
                'Actual compiled binary lacks compact storage capability')
        set_profile_allocator(Allocator(compiled_plan, compiled))
        actual = launch(token)
        require(actual.hash == compiled.hash, 'Launch binary differs from admitted plan')
        calls.append({'name': name, 'kind': 'explicit_automatic_record_capture'})
        require(len(allocations) == count + 1, 'Not one allocation per requested launch')
        owner = allocations[-1]
        completion = torch.cuda.Event()
        completion.record(owner['stream'])
        completion.synchronize()
        raw = owner['buffer'].cpu().numpy().tobytes()
        canary = owner['allocation'][len(raw):].cpu().numpy().tobytes()
        require(canary == bytes([165]) * 256, 'Compact allocation canary changed')
        (a.output / (name + '.canary')).write_bytes(canary)
        (a.output / (name + '.raw')).write_bytes(raw)
        context = ir.context()
        ir.load_dialects(context)
        nvidia.load_dialects(context)
        binding.load_dialects(context)
        artifacts = {}
        for suffix, value in compiled.asm.items():
            path = a.output / (name + '.' + suffix)
            path.write_bytes(value if isinstance(value, bytes) else str(value).encode())
            artifacts[suffix] = {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        module = ir.parse_mlir_module(str(a.output / (name + '.ttgir')), context)
        module.context = context
        plan = binding.get_automatic_proton_plan(module)
        require(plan['timeline_plan_version'] == 1, 'Wrong timeline planner')
        mechanisms = [r for r in plan['inventory'] if r.get('timeline_mechanism')]
        require(len(mechanisms) == plan['timeline_async_boundary_count'] and
                all(r['selected'] for r in mechanisms),
                'Incomplete compiler async boundary set')
        if name.startswith('gemm'):
            require({r['timeline_mechanism'] for r in mechanisms} == {
                'nvidia.cp_async.submit', 'nvidia.cp_async.commit', 'nvidia.cp_async.wait'},
                'Real ordinary GEMM lost its supported async mechanism')
        scopes = dict(binding.get_scope_id_names(module))
        decoded = decoder.decode_timeline_ring(
            raw, scratch_size=owner['stride'], total_warps=4,
            selected_warps=(0, 1, 2, 3),
            slots=owner['layout']['slots'],
            scope_ids=frozenset(scopes))
        save(name + '.decoded.json', decoded)
        require(all(row['capacity_records'] == mode.buffer_size // (4 * 16)
                    for row in decoded['observers']),
                'Compiler silently changed the explicitly requested capacity')
        require(decoded['complete'], 'Default probe overflowed or saturated')
        facts = derive_cp_async_facts(
            decoded, dict(plan, binary_id=compiled.hash),
            capture_id='probe-' + capture_namespace + '-' + str(len(rows)),
            invocation_id='launch-' + capture_namespace + '-' + str(len(rows)),
            binary_id=compiled.hash)
        save(name + '.async-facts.json', facts)
        if name.startswith('gemm'):
            require(facts['groups'] and facts['waits'] and facts['dependencies'],
                    'Real GEMM has no reconstructed group/wait coverage')
            require(all(not row['groups_not_covered_by_observed_wait']
                        for row in facts['observers']),
                    'Real GEMM final drain did not cover every recorded group')
        require({r['program'] for r in decoded['records']} == set(owner['layout']['programs']),
                'Actual sampled programs differ from request')
        require(len(raw) == len(owner['layout']['slots']) * owner['stride'],
                'Capture allocated full-grid instead of compact scratch')
        pending, pairs = {}, []
        for event in decoded['records']:
            key = (event['program'], event['warp'], event['site'])
            if event['phase'] == 'entry':
                require(key not in pending, 'Duplicate entry without exit')
                pending[key] = event
            else:
                require(key in pending, 'Exit without retained entry')
                begin = pending.pop(key)
                pairs.append({'program': event['program'], 'warp': event['warp'],
                              'site': event['site'], 'begin_sequence': begin['sequence'],
                              'end_sequence': event['sequence'], 'begin_tick': begin['tick'],
                              'end_tick': event['tick'],
                              'raw_offsets': [begin['raw_byte_offset'], event['raw_byte_offset']]})
        require(not pending, 'Unclosed region')
        require(len({r['site'] for r in pairs if r['end_tick'] > r['begin_tick']}) >= 2,
                'No two positive actual internal regions')
        save(name + '.decoded.json', decoded)
        save(name + '.pairs.json', pairs)
        save(name + '.plan.json', plan)
        rows.append(dict(name=name, binary_hash=compiled.hash, raw_bytes=len(raw),
                         raw_sha256=hashlib.sha256(raw).hexdigest(), records=len(decoded['records']),
                         pairs=len(pairs), plan=plan, artifacts=artifacts,
                         async_groups=len(facts['groups']),
                         async_waits=len(facts['waits']),
                         async_dependencies=len(facts['dependencies']),
                         max_tick=max(r['tick'] for r in decoded['records']),
                         grid=owner['grid'], scratch_size=owner['stride'],
                         selected_programs=list(owner['layout']['programs']),
                         layout=owner['layout'], canary_intact=True))
        save('captures.json', rows)
        backend.instrumentation = previous
        set_profile_allocator(NullAllocator())
        return compiled

    try:
        x_cpu = torch.rand(129, dtype=torch.float32)
        x = x_cpu.cuda()
        y = torch.full((137,), -17.25, dtype=torch.float32, device='cuda')
        k_device = torch.empty((), dtype=torch.int32, device='cuda')
        state = torch.zeros(3, dtype=torch.int32, device='cuda')
        hashes = []
        for k in (3, 7, 11):
            expected = x_cpu.clone()
            for _ in range(k):
                expected = expected * 0.75 + 0.125
            k_device.fill_(k)
            for detailed in (False, True):
                y.fill_(-17.25)
                state.zero_()
                launch = lambda token, warmup=False: recurrence[(3,)](x, y, k_device, state, 129, 64,
                                                        num_warps=4, instrumentation_mode=token, warmup=warmup)
                if detailed:
                    compiled = collect('recurrence-k' + str(k), launch, (0, 2))
                    hashes.append(compiled.hash)
                else:
                    launch('')
                    calls.append({'name': 'recurrence-k' + str(k), 'kind': 'ordinary'})
                require(torch.allclose(y[:129].cpu(), expected, rtol=2e-6, atol=2e-6), 'Recurrence math changed')
                require(torch.equal(y[129:].cpu(), torch.full((8,), -17.25)), 'Tail canary changed')
                require(state.cpu().tolist() == [1, 1, 1], 'Program side-effect missing')
                require(torch.equal(x.cpu(), x_cpu), 'Recurrence input changed')
        require(len(set(hashes)) == 1, 'Runtime K recompiled the instrumented binary')
        left_cpu = torch.randn(48, 96, dtype=torch.float16)
        right_cpu = torch.randn(96, 56, dtype=torch.float16)
        left, right = left_cpu.cuda(), right_cpu.cuda()
        result = torch.empty((48, 56), dtype=torch.float32, device='cuda')
        reference = left_cpu.double() @ right_cpu.double()
        for stages in (2, 3):
            for detailed in (False, True):
                launch = lambda token, warmup=False: gemm[(2, 2)](left, right, result, 48, 56, 96, 32, 32, 32,
                                                    num_warps=4, num_stages=stages, instrumentation_mode=token, warmup=warmup)
                if detailed:
                    collect('gemm-stages' + str(stages), launch, None)
                else:
                    launch('')
                    calls.append({'name': 'gemm-stages' + str(stages), 'kind': 'ordinary'})
                require(torch.allclose(result.cpu().double(), reference, rtol=1e-2, atol=1e-2), 'GEMM math changed')
                require(torch.equal(left.cpu(), left_cpu) and torch.equal(right.cpu(), right_cpu), 'GEMM input changed')
        grid_input_cpu = torch.rand(960, dtype=torch.float32)
        grid_input = grid_input_cpu.cuda()
        grid_output = torch.empty(968, dtype=torch.float32, device='cuda')
        grid_state = torch.empty(15, dtype=torch.int32, device='cuda')
        grid_hashes = []
        for index, geometry in enumerate(((1, 1, 1), (7, 1, 1), (3, 5, 1), (1, 1, 1))):
            count = prod(geometry)
            n = count * 64 - 3
            for detailed in (False, True):
                grid_output.fill_(-17.25)
                grid_state.zero_()
                launch = lambda token, warmup=False: grid_map[geometry](
                    grid_input, grid_output, grid_state, n, 64, num_warps=4,
                    instrumentation_mode=token, warmup=warmup)
                name = 'grid-map-' + str(index)
                if detailed:
                    compiled = collect(name, launch, None)
                    grid_hashes.append(compiled.hash)
                else:
                    launch('')
                    calls.append({'name': name, 'kind': 'ordinary'})
                require(torch.allclose(grid_output[:n].cpu(),
                    grid_input_cpu[:n] * 0.625 + 0.25, rtol=2e-6, atol=2e-6),
                    'Grid-map math changed')
                require(torch.equal(grid_output[n:].cpu(), torch.full((968-n,), -17.25)),
                        'Grid-map tail canary changed')
                require(grid_state.cpu().tolist() == [1] * count + [0] * (15-count),
                        'Grid-map ordinary invocation was replayed or program mapping changed')
                require(torch.equal(grid_input.cpu(), grid_input_cpu), 'Grid-map input changed')
        require(len(set(grid_hashes)) == 1, 'Runtime grid facts leaked into the binary cache key')
        save('result.json', {'status': 'real_record_v2_math_passed_not_full_P01',
                            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            'decoder_sha256': hashlib.sha256(module_path.read_bytes()).hexdigest(),
                            'python': sys.executable, 'calls': calls, 'captures': len(rows),
                            'limitations': ['No public timeline API/CLI yet',
                                           'Logical cp.async group facts are not verified time arrows or Perfetto acceptance',
                                           'No cross-SM epoch or final marker-order certificate',
                                           'Test collector synchronizes each explicit capture; production deferred owner remains pending']})
    finally:
        backend.instrumentation = previous
        set_profile_allocator(NullAllocator())
        # Only this test's kernels were submitted in its process; keep buffers
        # alive until their writers are known finished, including failure paths.
        for owner in allocations:
            owner['stream'].synchronize()


if __name__ == '__main__':
    main()
