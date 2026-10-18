"""Target-specific counter *unit* evidence, without clock/region certification.

PTX ISA 9.4 §10.28 defines the 64-bit globaltimer in nanoseconds and warns its
behavior is target-specific. Require the real binary's validated machine map,
and currently restrict this provider to the actually inspected sm_120 target.
https://docs.nvidia.com/cuda/parallel-thread-execution/#special-registers-globaltimer-globaltimer-lo-globaltimer-hi
"""
import hashlib
import json
from pathlib import Path
from .timeline_events import validate_raw_batch, _integer
from .timeline_views import CounterUnitProof, document_sha256


def nvidia_counter_unit_proofs(batch, *, machine_map, max_elapsed_ns):
    """Consume a freshly validated map, not a caller's clock_verified flag."""
    batch = validate_raw_batch(batch)
    _integer(max_elapsed_ns, 'independent host elapsed window', 1)
    if (type(machine_map) is not dict or machine_map.get('status')
            != 'counter_mapping_complete_region_unverified'
            or machine_map.get('binary_id') != batch['identity']['binary_id']
            or machine_map.get('expected_sm') != [12, 0]
            or any(type(v) is not int for v in machine_map['expected_sm'])):
        raise ValueError(
            'Counter unit provider requires the actual sm_120 machine map')
    rows = machine_map.get('counter_pcs')
    if type(rows) is not list or not rows:
        raise ValueError('Machine map lacks actual counter instructions')
    from .timeline_nvidia_machine import is_globaltimer_getter
    mapped = set()
    for row in rows:
        if (type(row) is not dict or not is_globaltimer_getter(
                row.get('opcode'), row.get('operands'))
                or type(row.get('site_id')) is not int or row['site_id'] < 0
                or row.get('phase') not in ('entry', 'exit')):
            raise ValueError(
                'Counter unit provider does not recognize this actual getter')
        mapped.add((str(row.get('site_id')), row.get('phase')))
    sites = {row['id']: row for row in batch['sites']}
    records = {row['id']: row for row in batch['records']}
    for event in batch['events']:
        site = sites[event['site_id']]
        phases = ['entry', 'exit'] if event['kind'] == 'interval' else [
            records[key]['phase'] for key in event['record_ids']
        ]
        if any((site['backend_site_id'], phase) not in mapped
               for phase in phases):
            raise ValueError(
                'Observed site/phase is absent from the actual machine map')
    if any(row['timer_bits'] != 64 for row in batch['observers']):
        raise ValueError(
            'NVIDIA unit provider requires full-width timer records')
    digest = document_sha256(machine_map)
    from . import timeline_nvidia_machine
    implementation = document_sha256({
        'unit_provider':
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'machine_rules':
        hashlib.sha256(Path(
            timeline_nvidia_machine.__file__).read_bytes()).hexdigest()
    })
    return [
        CounterUnitProof(**batch['identity'],
                         raw_sha256=batch['raw_artifact']['sha256'],
                         observer_id=observer['id'],
                         period_numerator_ns=1,
                         period_denominator=1,
                         max_elapsed_ns=max_elapsed_ns,
                         provider='nvidia.sm120.globaltimer_counter_unit.v1',
                         implementation_sha256=implementation,
                         evidence_ids=('nvidia.PTX_ISA_9.4.section_10.28',
                                       'actual_machine_map_sha256:' + digest))
        for observer in batch['observers']
    ]


def load_counter_machine_map(directory, capture):
    """Revalidate retained machine inputs before deriving unit-only views.

    Cached JSON status is not a clock proof. Recompute the binary/PTX/SASS map
    and check all of its fields, using the existing pure actual-object parser.
    """
    from .timeline_nvidia_machine import counter_map
    from .timeline_store import read_artifact
    directory = Path(directory)
    status = capture['machine_counter_mapping']
    kind = status.get('status')
    if kind not in ('counter_mapping_complete_region_unverified',
                    'counter_mapping_unavailable'):
        raise ValueError('Actual machine counter inputs are unavailable')
    metadata = capture['metadata']
    artifacts = metadata['timeline_artifacts']

    def retained(suffix):
        rows = [
            row for row in artifacts if row['retained_file'].endswith(suffix)
        ]
        if len(rows) != 1:
            raise ValueError('Missing or ambiguous retained unit artifact')
        row = rows[0]
        raw = read_artifact(directory, row['retained_file'])
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Counter unit input artifact changed')
        return raw

    binary = metadata['binary_id']
    if status.get('binary_id') != binary:
        raise ValueError('Machine status references another binary')
    machine_base = 'machine/' + binary
    expected = machine_base + '/counter-map.json'
    if kind == 'counter_mapping_complete_region_unverified':
        if status.get('counter_map_file') != expected:
            raise ValueError('Machine map references another binary')
        saved = json.loads(read_artifact(directory, expected))
    else:
        if status.get('counter_map_file') is not None:
            raise ValueError('Failed machine status unexpectedly claims a map')
        saved = None
    target = metadata['compiler_metadata']['target']
    if target.get('backend') != 'cuda' or type(target.get('arch')) is not int:
        raise ValueError('Counter unit target is not actual CUDA metadata')
    arch = target['arch']
    actual = counter_map(
        cubin=retained('.cubin'),
        ptx=retained('.ptx'),
        sass_lines=read_artifact(directory, machine_base + '/lines.stdout'),
        sass_json=read_artifact(directory, machine_base + '/json.stdout'),
        binary_id=metadata['binary_id'],
        scope_ids=tuple(int(key) for key, _ in metadata['scope_id_names']),
        expected_sm=(arch // 10, arch % 10),
        marker_version=capture['owner']['plan']['timeline_marker_version'])
    if saved is not None and any(
            saved.get(key) != value for key, value in actual.items()):
        raise ValueError(
            'Retained counter map differs from actual object validation')
    return actual


def load_counter_unit_proofs(directory, capture, batch):
    """Revalidate original objects; an old failed status never grants proof.

    Complete tool outputs retained by an older rule may be parsed by a newer
    rule without running the application or rewriting the original status.
    """
    actual = load_counter_machine_map(directory, capture)
    owner = capture['owner']
    if owner.get('host_window_clock') != 'python.monotonic_ns':
        raise ValueError('Capture lacks an independent host completion window')
    start, stop = owner.get('host_admission_ns'), owner.get(
        'host_completion_observed_ns')
    _integer(start, 'host admission ns')
    _integer(stop, 'host completion observed ns')
    if stop <= start:
        raise ValueError('Capture host completion window is invalid')
    return nvidia_counter_unit_proofs(batch,
                                      machine_map=actual,
                                      max_elapsed_ns=stop - start)
