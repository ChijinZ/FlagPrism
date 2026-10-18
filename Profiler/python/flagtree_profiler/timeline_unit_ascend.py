"""A2/c220 SYS_CNT unit evidence, without source-cost or shared-clock rights.

The documented A2 system counter is 50 MHz; GetSystemCycle belongs to PIPE_S.
We add no synchronization to make other engines look synchronous. Read precision
and cross-observer epochs remain unknown. This provider requires actual runtime
model, final clock instruction mappings, raw identity and a bounded host window.
"""
import hashlib
from pathlib import Path
import re
import struct

from .timeline_events import validate_raw_batch, _integer
from .timeline_views import CounterUnitProof, document_sha256
from . import timeline_ascend_machine
from .timeline_store import read_artifact

REFERENCE = (
    'https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/'
    'API/ascendcopapi/docs/en/api/SIMD-API/basic_api/tool_interface/'
    'system_resources_and_variables/GetSystemCycle_ISASI.md')


def _need(value, message):
    if not value:
        raise ValueError(message)


def load_counter_unit_proofs(directory, capture, batch):
    batch = validate_raw_batch(batch)
    metadata, owner = capture['metadata'], capture['owner']
    _need(
        all(batch['identity'][key] == owner[key]
            for key in ('capture_id', 'invocation_id', 'binary_id'))
        and batch['raw_artifact']['sha256'] == capture['raw_sha256'],
        'Counter unit inputs belong to different captures')
    runtime = metadata.get('runtime_device') or {}
    arch = metadata['compiler_metadata'].get('arch')
    _need(
        type(arch) is str and re.fullmatch(r'Ascend910B[0-9-]*', arch)
        and runtime.get('name') == arch and type(runtime.get('device')) is int
        and runtime['device'] == owner.get('device'),
        'A2 SYS_CNT unit requires the actual bound Ascend910B runtime target')
    _need(
        owner.get('host_window_clock') == 'python.monotonic_ns',
        'Missing independent host observation window')
    start, stop = owner.get('host_admission_ns'), owner.get(
        'host_completion_observed_ns')
    _integer(start, 'host admission ns')
    _integer(stop, 'host completion ns')
    # A conservative 32-bit wrap window also protects narrower implementations
    # of the API's returned i64. No timing is fitted from the profiled kernel.
    _need(
        0 < stop - start < 20 * (1 << 32),
        'Host observation window exceeds the conservative counter-wrap bound')
    _need(
        batch['records'] and max(row['tick']
                                 for row in batch['records']) >= (1 << 32),
        'Observed counter values do not establish the conservative width floor'
    )
    raw = read_artifact(directory, capture['raw_file'])
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Counter unit raw input changed')
    _need(
        all(0 <= row['offset'] <= len(raw) - 8
            and struct.unpack_from('<Q', raw, row['offset'])[0] == row['tick']
            for row in batch['records']),
        'Counter unit canonical tick differs from actual raw bytes')
    mapped = timeline_ascend_machine.load_counter_machine_map(
        directory, capture)
    _need(
        mapped['binary_id'] == batch['identity']['binary_id'] ==
        owner['binary_id'], 'Counter unit evidence belongs to another binary')
    phases = {(row['backend_site_id'], row['phase'])
              for row in mapped['counter_pcs']}
    sites = {row['id']: row for row in batch['sites']}
    for event in batch['events']:
        _need(event['kind'] == 'interval',
              'Unexpected Ascend endpoint semantics')
        key = sites[event['site_id']]['backend_site_id']
        _need(all((key, phase) in phases for phase in ('entry', 'exit')),
              'Observed endpoint is absent from actual machine mappings')
    _need(all(row['timer_bits'] == 64 for row in batch['observers']),
          'SYS_CNT unit provider requires full returned i64 records')
    implementation = document_sha256({
        'unit_provider':
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'machine_rules':
        hashlib.sha256(Path(
            timeline_ascend_machine.__file__).read_bytes()).hexdigest()
    })
    return [
        CounterUnitProof(**batch['identity'],
                         raw_sha256=batch['raw_artifact']['sha256'],
                         observer_id=observer['id'],
                         period_numerator_ns=20,
                         period_denominator=1,
                         max_elapsed_ns=stop - start,
                         provider='ascend.c220.A2.SYS_CNT_counter_unit.v1',
                         implementation_sha256=implementation,
                         evidence_ids=(REFERENCE,
                                       'actual_machine_map_sha256:' +
                                       document_sha256(mapped),
                                       'runtime_target:' + arch,
                                       'independent_host_window_ns:' +
                                       str(stop - start)))
        for observer in batch['observers']
    ]
