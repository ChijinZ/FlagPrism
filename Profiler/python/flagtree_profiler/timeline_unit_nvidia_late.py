"""SM120 late-reader counter units, with actual object/marker verification.

PTX ISA 9.4 section 10.28 specifies globaltimer in nanoseconds but warns that
behavior is target-specific. This provider restricts itself to inspected SM120
full-width machine readers. No read-precision, shared epoch, source cost or
hardware activity certificate follows.
https://docs.nvidia.com/cuda/parallel-thread-execution/#special-registers-globaltimer-globaltimer-lo-globaltimer-hi
"""
import hashlib
import json
from pathlib import Path

from .timeline_events import validate_raw_batch, _integer
from .timeline_views import CounterUnitProof, document_sha256


def late_expected_phases(manifest):
    result, sites = [], set()
    for site in manifest['sites']:
        key = _integer(site.get('site_id'), 'late site', 1, (1 << 31) - 1)
        if key in sites:
            raise ValueError('Duplicate late source site')
        sites.add(key)
        semantic = site.get('record_semantics')
        if semantic not in ('observer_checkpoint_after',
                            'observer_issue_bracket'):
            raise ValueError('Unknown late source record semantics')
        phases = ('exit', ) if semantic == 'observer_checkpoint_after' else (
            'entry', 'exit')
        result.extend((key, phase) for phase in phases)
    if not result or len(sites) > 4096:
        raise ValueError('Late marker inventory is empty or oversized')
    return tuple(result)


def inspect_late_capture_binary(directory, *, metadata, plan, deadline):
    from .timeline_nvidia_machine import inspect_capture_binary
    physical = dict(plan, timeline_marker_version=1)
    return inspect_capture_binary(directory,
                                  metadata=metadata,
                                  plan=physical,
                                  deadline=deadline,
                                  marker_flavor='late-v1',
                                  scope_ids=tuple(site['site_id']
                                                  for site in plan['sites']),
                                  expected_phases=late_expected_phases(plan),
                                  inspect_wait_control=False)


def load_late_machine_map(directory, capture):
    from .timeline_nvidia_machine import counter_map
    from .timeline_store import read_artifact
    metadata, owner = capture['metadata'], capture['owner']
    binary = metadata['binary_id']
    if binary != owner['binary_id']:
        raise ValueError(
            'Late machine inputs belong to a different invocation binary')
    status = capture.get('machine_counter_mapping') or {}
    if status.get('status') not in (
            'counter_mapping_complete_region_unverified',
            'counter_mapping_unavailable'):
        raise ValueError(
            'Late machine object/disassembly inputs are unavailable')
    target = metadata['compiler_metadata']['target']
    arch = target.get('arch')
    if target.get('backend') != 'cuda' or type(arch) is not int:
        raise ValueError('Late machine target lacks actual CUDA metadata')

    def artifact(suffix):
        rows = [
            row for row in metadata['timeline_artifacts']
            if row['retained_file'].endswith(suffix)
        ]
        if len(rows) != 1:
            raise ValueError('Missing or ambiguous late machine input ' +
                             suffix)
        row = rows[0]
        data = read_artifact(directory, row['retained_file'])
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Retained late machine input changed')
        return data

    base = 'machine/' + binary
    actual = counter_map(cubin=artifact('.cubin'),
                         ptx=artifact('.ptx'),
                         sass_lines=read_artifact(directory,
                                                  base + '/lines.stdout'),
                         sass_json=read_artifact(directory,
                                                 base + '/json.stdout'),
                         binary_id=binary,
                         scope_ids=tuple(site['site_id']
                                         for site in owner['plan']['sites']),
                         expected_sm=(arch // 10, arch % 10),
                         marker_version=1,
                         marker_flavor='late-v1',
                         expected_phases=late_expected_phases(owner['plan']))
    if status.get('status') == 'counter_mapping_complete_region_unverified':
        if status.get('counter_map_file') != base + '/counter-map.json':
            raise ValueError(
                'Late machine map path differs from the actual binary')
        saved = json.loads(read_artifact(directory,
                                         status['counter_map_file']))
        if any(saved.get(key) != value for key, value in actual.items()):
            raise ValueError(
                'Late saved counter map differs from original object validation'
            )
    elif status.get('counter_map_file') is not None:
        raise ValueError(
            'Unavailable late map cannot claim a successful map artifact')
    return actual


def late_counter_unit_proofs(batch, *, machine_map, max_elapsed_ns):
    from .timeline_nvidia_machine import is_globaltimer_getter
    batch = validate_raw_batch(batch)
    _integer(max_elapsed_ns, 'independent host elapsed window', 1)
    if (machine_map.get('status')
            != 'counter_mapping_complete_region_unverified'
            or machine_map.get('marker_flavor') != 'late-v1'
            or machine_map.get('expected_sm') != [12, 0]
            or any(type(v) is not int for v in machine_map['expected_sm'])
            or machine_map.get('binary_id') != batch['identity']['binary_id']):
        raise ValueError(
            'Late units require the inspected SM120 machine/marker map')
    mapped = set()
    rows = machine_map.get('counter_pcs')
    if type(rows) is not list or not rows:
        raise ValueError('Late machine map has no actual counter PCs')
    for row in rows:
        if (not is_globaltimer_getter(row.get('opcode'), row.get('operands'))
                or type(row.get('site_id')) is not int or row['site_id'] < 1
                or row.get('phase') not in ('entry', 'exit')):
            raise ValueError('Unrecognized actual late machine getter')
        mapped.add((str(row['site_id']), row['phase']))
    sites = {row['id']: row for row in batch['sites']}
    for record in batch['records']:
        if (sites[record['site_id']]['backend_site_id'], 'exit' if
                record['phase'] == 'point' else record['phase']) not in mapped:
            raise ValueError(
                'Actual late endpoint lacks its marked machine getter')
    if any(observer['timer_bits'] != 64 for observer in batch['observers']):
        raise ValueError('Late counter unit requires full-width timer records')
    from . import timeline_nvidia_machine
    implementation = document_sha256(
        dict(provider=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             machine_rules=hashlib.sha256(
                 Path(timeline_nvidia_machine.__file__).read_bytes()).
             hexdigest()))
    return [
        CounterUnitProof(
            **batch['identity'],
            raw_sha256=batch['raw_artifact']['sha256'],
            observer_id=observer['id'],
            period_numerator_ns=1,
            period_denominator=1,
            max_elapsed_ns=max_elapsed_ns,
            provider='nvidia.sm120.late_globaltimer_counter_unit.v1',
            implementation_sha256=implementation,
            evidence_ids=('nvidia.PTX_ISA_9.4.section_10.28',
                          'actual_machine_map_sha256:' +
                          document_sha256(machine_map)))
        for observer in batch['observers']
    ]


def load_late_counter_unit_proofs(directory, capture, batch):
    owner = capture['owner']
    if owner.get('host_window_clock') != 'python.monotonic_ns':
        raise ValueError(
            'Late capture lacks an independent host completion window')
    start = _integer(owner.get('host_admission_ns'), 'host admission ns')
    stop = _integer(owner.get('host_completion_observed_ns'),
                    'host completion observed ns')
    if stop <= start:
        raise ValueError('Late host completion window is invalid')
    return late_counter_unit_proofs(batch,
                                    machine_map=load_late_machine_map(
                                        directory, capture),
                                    max_elapsed_ns=stop - start)
