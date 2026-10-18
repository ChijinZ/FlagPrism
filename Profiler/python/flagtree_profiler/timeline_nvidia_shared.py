"""SM120 same-invocation/CTA global counter epoch provider.

NVIDIA CCCL documents its device system_clock implementation with globaltimer
and steadiness within device code. We combine that semantic source with the
actual full-width SM120 object getter, exact raw/manifest binding and one native
CTA. No host clock correlation, quantitative read error or flow is inferred.
"""
import hashlib
from collections import defaultdict
from pathlib import Path

from .timeline_events import stable_id, _integer
from .timeline_shared import SharedCounterProof
from .timeline_views import document_sha256

REFERENCE = {
    'url':
    'https://nvidia.github.io/cccl/unstable/libcudacxx/standard_api/time_library.html',
    'section':
    'Implementation-Defined Behavior / system_clock / device code',
    'accessed_utc':
    '2026-10-18',
    'excerpt':
    'PTX’s %globaltimer is a system clock which also happens to be monotonically increasing on today’s NVIDIA GPUs',
    'scope':
    'device counter semantics; no quantitative endpoint error bound or host correlation'
}


def load_shared_counter_inputs(directory, capture, raw):
    from .timeline_events_nvidia_late import canonicalize_late_capture
    from .timeline_unit_nvidia_late import load_late_machine_map, late_counter_unit_proofs
    from . import timeline_nvidia_machine, timeline_unit_nvidia_late
    owner, metadata = capture['owner'], capture['metadata']
    plan, layout = owner['plan'], owner['layout']
    compiled = metadata['compiler_metadata']
    if (layout.get('storage_version') != 'nvidia-late-1'
            or type(layout.get('num_ctas')) is not int
            or layout['num_ctas'] != 1
            or type(compiled.get('num_ctas')) is not int
            or compiled['num_ctas'] != 1
            or owner.get('submission_outcome') != 'returned'
            or owner.get('completion_known') is not True
            or owner.get('readback_integrity', {}).get('status') != 'passed'):
        raise ValueError(
            'Shared counter provider requires one completed native CTA per program'
        )
    _integer(owner.get('device'), 'actual CUDA device')
    _integer(owner.get('stream'), 'actual CUDA stream')
    if owner.get('host_window_clock') != 'python.monotonic_ns':
        raise ValueError('Missing independent completion window')
    start = _integer(owner.get('host_admission_ns'), 'host admission')
    stop = _integer(owner.get('host_completion_observed_ns'),
                    'host completion')
    if stop <= start:
        raise ValueError('Invalid actual host completion window')
    actors = _integer(plan.get('actors'), 'recorded actors', 2)
    warp = _integer(compiled.get('warp_size'), 'actual compiler warp width', 1)
    if warp != 32:
        raise ValueError(
            'SM120 native warp geometry differs from this provider')
    if plan.get('dependency_footprint_complete') is True:
        dimensions = plan.get('block_dimensions')
        if (type(dimensions) is not list or len(dimensions) != 3
                or any(type(x) is not int or x <= 0 for x in dimensions)
                or dimensions[0] * dimensions[1] * dimensions[2] != actors
                or actors != compiled['num_warps'] * warp):
            raise ValueError(
                'Actual full-CTA recorder geometry differs from compiled function'
            )
        indices = tuple(i * warp for i in range(min(4, compiled['num_warps'])))
    else:
        indices = tuple(range(min(4, actors)))
    if len(indices) < 2:
        raise ValueError(
            'Shared view requires at least two actual recorded threads')
    batch = canonicalize_late_capture(raw,
                                      owner=owner,
                                      metadata=metadata,
                                      actor_indices=indices)
    for observer in batch['observers']:
        thread = observer['attributes']['nvidia.thread_flat_index']
        observer['attributes'].update({
            'nvidia.warp_id': thread // warp,
            'nvidia.lane_id': thread % warp
        })
    mapping = load_late_machine_map(directory, capture)
    # This validates actual SM120 full-width readers at every selected endpoint,
    # not a cached "clock verified" flag or a register's printed name alone.
    late_counter_unit_proofs(batch,
                             machine_map=mapping,
                             max_elapsed_ns=stop - start)
    implementation = document_sha256(
        dict(provider=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             unit_rules=hashlib.sha256(
                 Path(timeline_unit_nvidia_late.__file__).read_bytes()
             ).hexdigest(),
             machine_rules=hashlib.sha256(
                 Path(timeline_nvidia_machine.__file__).read_bytes()).
             hexdigest()))
    context = document_sha256(
        dict(identity=batch['identity'],
             device=owner['device'],
             stream=owner['stream'],
             admission_ns=start,
             completion_ns=stop,
             num_ctas=1,
             reference=REFERENCE,
             machine=document_sha256(mapping)))
    groups = defaultdict(list)
    for observer in batch['observers']:
        groups[tuple(observer['program_coordinates'])].append(observer['id'])
    proofs = []
    for coordinates, observer_ids in groups.items():
        domain = stable_id(
            tuple(batch['identity'][k]
                  for k in ('capture_id', 'invocation_id', 'binary_id')),
            'shared-device-counter', context, coordinates)
        proofs.append(
            SharedCounterProof(
                **batch['identity'],
                raw_sha256=batch['raw_artifact']['sha256'],
                canonical_sha256=document_sha256(batch),
                observer_ids=tuple(observer_ids),
                program_coordinates=coordinates,
                domain_id=domain,
                epoch_id=stable_id((), 'shared-counter-capture-epoch',
                                   context),
                period_numerator_ns=1,
                period_denominator=1,
                max_elapsed_ns=stop - start,
                provider='nvidia.sm120.same_invocation_cta_globaltimer.v1',
                implementation_sha256=implementation,
                evidence_ids=('NVIDIA.CCCL.device_clock_reference_sha256:' +
                              document_sha256(REFERENCE),
                              'actual_machine_map_sha256:' +
                              document_sha256(mapping),
                              'actual_capture_context_sha256:' + context)))
    return batch, proofs
