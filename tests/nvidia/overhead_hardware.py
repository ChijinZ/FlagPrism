"""Randomized 3x30 measurements with an independent CUPTI activity reference.

The same independent reference parser runs in every SDK-on phase through a
CUPTI callback fanout proxy. SDK-off CUDA events describe stream envelopes only.
"""
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import torch
import triton
import triton.language as tl
import triton._C.libtriton as libtriton
import flagtree

source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler import language as pl
from flagtree.profiler.hooks.hook import Hook, HookManager
from flagtree.profiler.observations import ObservationRequest
from flagtree.profiler.native import runtime_binding

pl.enable_semantic('triton')


@triton.jit
def workload(X, W, Y, N: tl.constexpr, BLOCK: tl.constexpr):
    row = tl.program_id(0)
    column = tl.arange(0, BLOCK)
    pl.enter_scope('rms_source_control')
    value = tl.load(X + row * N + column, column < N, 0)
    scale = tl.rsqrt(tl.sum(value * value, 0) / N + 1.e-5)
    weight = tl.load(W + column, column < N, 0)
    result = value * scale * weight
    pl.exit_scope('rms_source_control')
    tl.store(Y + row * N + column, result, column < N)


class IdentityObserver(Hook):
    priority = -100
    last = None

    def activate(self):
        pass

    def deactivate(self):
        pass

    def init_handle(self, *args):
        pass

    def enter(self, metadata):
        self.last = dict(metadata._flagprism_invocation_identity)

    def exit(self, metadata):
        pass


output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
reference_library = Path(os.environ['METHOD_REFERENCE_CUPTI'])
ref = ctypes.CDLL(str(reference_library))
ref.reference_json.restype = ctypes.c_char_p
ref.reference_push.argtypes = [ctypes.c_uint64]
inputs = Path(os.environ['METHOD_CANONICAL_INPUTS'])
raw_x = (inputs / 'rows-127x769-0.bin').read_bytes()
raw_w = (inputs / 'rows-127x769-1.bin').read_bytes()
cpu_x = torch.frombuffer(bytearray(raw_x),
                         dtype=torch.float32).reshape(127, 769).clone()
cpu_w = torch.frombuffer(bytearray(raw_w), dtype=torch.float32).clone()
expected = cpu_x * torch.rsqrt((cpu_x * cpu_x).mean(-1, keepdim=True) +
                               1.e-5) * cpu_w
x, w = cpu_x.cuda(), cpu_w.cuda()
y = torch.empty_like(x)


def invoke():
    return workload[(127, )](x, w, y, 769, 1024, num_warps=4, num_stages=1)


def checked(status):
    if status:
        raise RuntimeError(f'Independent CUPTI status {status}')


result = {
    'schema_version':
    1,
    'status':
    'running',
    'case':
    'preselected RMSNorm',
    'shape': [127, 769],
    'config': {
        'num_warps': 4,
        'num_stages': 1,
        'block': 1024
    },
    'input_sha256':
    [hashlib.sha256(raw_x).hexdigest(),
     hashlib.sha256(raw_w).hexdigest()],
    'batches':
    3,
    'samples_per_phase':
    30,
    'warmup':
    3,
    'order_seed':
    1729,
    'compiler_path':
    libtriton.__file__,
    'compiler_sha256':
    hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest(),
    'native_path':
    runtime_binding().__file__,
    'native_sha256':
    hashlib.sha256(Path(runtime_binding().__file__).read_bytes()).hexdigest(),
    'reference_collector_path':
    str(reference_library),
    'reference_collector_sha256':
    hashlib.sha256(reference_library.read_bytes()).hexdigest(),
    'reference_measurement_boundary':
    'Same independent CUPTI driver/kernel reference parser on in reference/native/detailed; callback fanout copies SDK records before primary free. Compare configuration-level runs; reference collector own cost retained.',
    'device_event_semantics':
    'CUDA stream envelope enclosing 30 calls, includes host submission/callback gaps; not actual kernel duration',
    'reference_perturbation_limit':
    'CUPTI reference collection has its own overhead; SDK-off actual device-task duration is unavailable',
    'identity_observer_cost':
    'Native/detailed phases include two small test observer callbacks that read the same launch metadata identity; not subtracted',
    'phases': []
}
(output / 'result.json').write_text(json.dumps(result, indent=2))
rng = random.Random(1729)
for batch in range(3):
    modes = [
        'off', 'reference', 'native', 'detailed_default', 'detailed_bounded'
    ]
    rng.shuffle(modes)
    for mode_name in modes:
        phase_name = f'b{batch}-{mode_name}'
        phase_dir = output / phase_name
        phase_dir.mkdir()
        start_prep = time.perf_counter_ns()
        native_session = detailed_session = None
        observer = None
        if mode_name in ('native', 'detailed_default', 'detailed_bounded'):
            native_session = profiler.start(str(phase_dir / 'native'),
                                            backend='cupti',
                                            hook='triton')
            if mode_name.startswith('detailed'):
                detailed_session = profiler.start(
                    str(phase_dir / 'detailed'),
                    backend='instrumentation',
                    hook='instrumentation',
                    observation_request=ObservationRequest(
                        programs=(0, ),
                        max_events_per_instance=256
                        if mode_name == 'detailed_default' else 4))
            observer = IdentityObserver()
            HookManager.register(
                observer, detailed_session
                if detailed_session is not None else native_session)
        reference_on = mode_name != 'off'
        if mode_name == 'reference': checked(ref.reference_start())
        elif reference_on: checked(ref.reference_begin_native())
        for warmup in range(3):
            if reference_on: checked(ref.reference_push(100 + warmup))
            compiled = invoke()
            if reference_on: checked(ref.reference_pop())
        torch.cuda.synchronize()
        preparation_ns = time.perf_counter_ns() - start_prep
        for kind in ('ttgir', 'llir', 'ptx'):
            (phase_dir / kind).write_text(compiled.asm[kind])
        clock_state = subprocess.run([
            'nvidia-smi',
            '--query-gpu=uuid,clocks.current.sm,clocks.current.memory,utilization.gpu,temperature.gpu',
            '--format=csv,noheader'
        ],
                                     capture_output=True,
                                     text=True).stdout.strip()
        begin, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(
            enable_timing=True)
        samples = []
        begin.record()
        for sample in range(30):
            external_id = 10000 + sample
            if reference_on: checked(ref.reference_push(external_id))
            start = time.perf_counter_ns()
            current = invoke()
            elapsed = time.perf_counter_ns() - start
            if reference_on: checked(ref.reference_pop())
            assert current.hash == compiled.hash
            samples.append({
                'sample':
                sample,
                'host_launch_ns':
                elapsed,
                'scope_id':
                observer.last['scope_id'] if observer is not None else None,
                'reference_external_id':
                external_id if reference_on else None
            })
        end.record()
        end.synchronize()
        envelope_ms = begin.elapsed_time(end)
        start_finalize = time.perf_counter_ns()
        device_records = []
        if reference_on:
            checked(ref.reference_stop())
            document = json.loads(ref.reference_json())
            assert document['dropped_records'] == 0
            (phase_dir / 'reference-raw.json').write_text(
                json.dumps(document, indent=2))
            identities = {
                sample['reference_external_id']
                for sample in samples
            }
            device_records = [
                record for record in document['records']
                if record['external_id'] in identities
            ]
        if detailed_session is not None: profiler.finalize(detailed_session)
        if native_session is not None:
            profiler.finalize(native_session)
            events = [
                json.loads(line) for line in (
                    phase_dir /
                    'native/ai/events.jsonl').read_text().splitlines()
            ]
            identities = {sample['scope_id'] for sample in samples}
            native_records = [{
                'start_ns': event['start_ns'],
                'end_ns': event['end_ns'],
                'scope_id': event['scope_id'],
                'correlation_key': event['correlation_key'],
                'correlation_id': event['correlation_id'],
                'device_id': event['device_id'],
                'context_id': event['context_id'],
                'stream_id': event['stream_id']
            } for event in events if event['kind'] == 'kernel'
                              and event['scope_id'] in identities]

            # Equality uses SDK correlation identities and endpoints, never
            # names or appearance order. The reference remains the device oracle.
            def sdk_identity(record):
                return tuple(record[field]
                             for field in ('device_id', 'context_id',
                                           'stream_id', 'correlation_id',
                                           'start_ns', 'end_ns'))

            native_intervals = {
                sdk_identity(record)
                for record in native_records
            }
            assert native_intervals == {
                sdk_identity(record)
                for record in device_records
            }, (phase_name, native_records, device_records)
            (phase_dir / 'native-reference-identity-check.json').write_text(
                json.dumps(
                    {
                        'basis':
                        'exact_sdk_device_context_stream_correlation_and_endpoints',
                        'native_records': native_records,
                        'matched_records': len(native_intervals)
                    },
                    indent=2))
        finalization_ns = time.perf_counter_ns() - start_finalize
        if mode_name != 'off':
            assert len(device_records) == 30, (phase_name, len(device_records))
            assert all(record['end_ns'] > record['start_ns']
                       for record in device_records)
        torch.testing.assert_close(y.cpu(), expected, atol=0.0005, rtol=0.002)
        durations = [
            record['end_ns'] - record['start_ns'] for record in device_records
        ]
        phase = {
            'batch':
            batch,
            'mode':
            mode_name,
            'binary_id':
            compiled.hash,
            'preparation_including_compile_warmup_ns':
            preparation_ns,
            'finalization_and_export_ns':
            finalization_ns,
            'cuda_stream_envelope_ms':
            envelope_ms,
            'clock_state_before_samples':
            clock_state,
            'samples':
            samples,
            'device_records':
            device_records,
            'host_launch_median_ns':
            statistics.median(sample['host_launch_ns'] for sample in samples),
            'device_task_median_ns':
            statistics.median(durations) if durations else None,
            'compiled_shared_bytes':
            compiled.metadata.shared,
            'artifact_bytes':
            sum(path.stat().st_size for path in phase_dir.rglob('*')
                if path.is_file()),
            'collection_scope':
            'device_selected_physical_CTA0_warp0'
            if mode_name.startswith('detailed') else None,
            'output_program_selection':
            [0] if mode_name.startswith('detailed') else None
        }
        result['phases'].append(phase)
        (output / 'result.json').write_text(json.dumps(result, indent=2))
        print('PASS PHASE',
              batch,
              mode_name,
              'host_median_ns',
              phase['host_launch_median_ns'],
              'device_median_ns',
              phase['device_task_median_ns'],
              flush=True)
result['status'] = 'passed'
summary = {}
for mode_name in [
        'off', 'reference', 'native', 'detailed_default', 'detailed_bounded'
]:
    phases = [
        phase for phase in result['phases'] if phase['mode'] == mode_name
    ]
    host = [
        sample['host_launch_ns'] for phase in phases
        for sample in phase['samples']
    ]
    device = [
        record['end_ns'] - record['start_ns'] for phase in phases
        for record in phase['device_records']
    ]
    summary[mode_name] = {
        'host_launch_median_ns': statistics.median(host),
        'device_task_median_ns': statistics.median(device) if device else None,
        'raw_sample_count': len(host),
        'device_sample_count': len(device)
    }
for mode_name, entry in summary.items():
    entry['host_ratio_to_SDK_off'] = entry['host_launch_median_ns'] / summary[
        'off']['host_launch_median_ns']
    entry['device_ratio_to_independent_reference'] = entry[
        'device_task_median_ns'] / summary['reference'][
            'device_task_median_ns'] if entry['device_task_median_ns'] else None
result['summary'] = summary
(output / 'result.json').write_text(json.dumps(result, indent=2))
print('PASS RANDOMIZED_3_BATCHES_X_30', json.dumps(summary), flush=True)
