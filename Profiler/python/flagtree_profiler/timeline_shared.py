"""Capture-bound shared counter coordinates, distinct from physical precision.

The backend proves a common counter epoch for an explicit observer set. The
common projection preserves original samples and never grants physical order,
source costs, engine activity or temporal flows from that fact alone.
"""
import copy
from dataclasses import dataclass

from .timeline_events import validate_raw_batch, _integer, _sha, _text
from .timeline_views import document_sha256
from .timeline_clock import TickScale


@dataclass(frozen=True)
class SharedCounterProof:
    capture_id: str
    invocation_id: str
    binary_id: str
    raw_sha256: str
    canonical_sha256: str
    observer_ids: tuple
    program_coordinates: tuple
    domain_id: str
    epoch_id: str
    period_numerator_ns: int
    period_denominator: int
    max_elapsed_ns: int
    provider: str
    implementation_sha256: str
    evidence_ids: tuple
    scope_kind: str = 'shared_observers'
    period_uncertainty_numerator_ns: int = 0
    period_uncertainty_denominator: int = 1

    def __post_init__(self):
        for field in ('capture_id', 'invocation_id', 'binary_id', 'domain_id',
                      'epoch_id', 'provider'):
            _text(getattr(self, field), field)
        for field in ('raw_sha256', 'canonical_sha256',
                      'implementation_sha256'):
            _sha(getattr(self, field))
        for field in ('period_numerator_ns', 'period_denominator',
                      'max_elapsed_ns'):
            _integer(getattr(self, field), field, 1)
        _integer(self.period_uncertainty_numerator_ns, 'period uncertainty')
        _integer(self.period_uncertainty_denominator,
                 'uncertainty denominator', 1)
        TickScale(self.period_numerator_ns, self.period_denominator,
                  self.period_uncertainty_numerator_ns,
                  self.period_uncertainty_denominator)
        if self.scope_kind not in ('shared_observers', 'single_observer'):
            raise ValueError('Unknown counter scope kind')
        minimum = 2 if self.scope_kind == 'shared_observers' else 1
        maximum = 64 if self.scope_kind == 'shared_observers' else 1
        if (type(self.observer_ids) is not tuple
                or not minimum <= len(self.observer_ids) <= maximum
                or len(set(self.observer_ids)) != len(self.observer_ids)):
            raise ValueError(
                'Shared counter proof requires distinct actual observers')
        for key in self.observer_ids:
            _text(key, 'shared observer ID')
        if type(self.program_coordinates) is not tuple or len(
                self.program_coordinates) != 3:
            raise ValueError('Shared counter scope must identify one program')
        for coordinate in self.program_coordinates:
            _integer(coordinate, 'shared program coordinate')
        if type(self.evidence_ids) is not tuple or not self.evidence_ids:
            raise ValueError(
                'Shared counter proof requires actual evidence references')
        for key in self.evidence_ids:
            _text(key, 'shared counter evidence')


def derive_shared_counter_view(canonical, proof):
    batch = validate_raw_batch(canonical)
    if not isinstance(proof, SharedCounterProof):
        raise TypeError(
            'Obtain a scoped counter-domain proof from the backend')
    if (any(
            getattr(proof, key) != batch['identity'][key]
            for key in ('capture_id', 'invocation_id', 'binary_id'))
            or proof.raw_sha256 != batch['raw_artifact']['sha256']
            or proof.canonical_sha256 != document_sha256(batch)):
        raise ValueError(
            'Shared counter proof belongs to another raw/canonical invocation')
    observers = {o['id']: o for o in batch['observers']}
    if proof.scope_kind == 'shared_observers' and not batch['complete']:
        raise ValueError(
            'Shared counter projection requires complete captured raw')
    chosen = []
    for key in proof.observer_ids:
        if key not in observers:
            raise ValueError('Shared proof names an absent observer')
        observer = observers[key]
        if (tuple(observer['program_coordinates']) != proof.program_coordinates
                or not observer['complete']):
            raise ValueError(
                'Shared proof crosses program scope or incomplete observers')
        chosen.append(observer)
    selected = set(proof.observer_ids)
    records = [r for r in batch['records'] if r['observer_id'] in selected]
    if {r['observer_id'] for r in records} != selected:
        raise ValueError(
            'Shared counter projection cannot invent empty observer coordinates'
        )
    origin, maximum = min(r['tick'] for r in records), max(r['tick']
                                                           for r in records)
    scale = TickScale(proof.period_numerator_ns, proof.period_denominator,
                      proof.period_uncertainty_numerator_ns,
                      proof.period_uncertainty_denominator)
    nominal_scale = TickScale(proof.period_numerator_ns,
                              proof.period_denominator)
    bits = {o['timer_bits'] for o in chosen}
    if len(bits) != 1:
        raise ValueError('Shared observers disagree on counter encoding width')
    scale.elapsed_ticks(origin,
                        maximum,
                        bits=bits.pop(),
                        max_elapsed_ns=proof.max_elapsed_ns)
    projected = {}
    for record in records:
        ns, rounding = nominal_scale.offset(record['tick'] - origin)
        projected[record['id']] = dict(record,
                                       relative_ns=ns,
                                       conversion_rounding_ns=rounding)
        if proof.period_uncertainty_numerator_ns:
            projected[
                record['id']]['conversion_scale_error_ns'] = scale.offset(
                    record['tick'] - origin)[1]
    events = []
    for event in batch['events']:
        if event['observer_id'] not in selected:
            continue
        refs = [projected[key] for key in event['record_ids']]
        events.append(
            dict(event,
                 start_ns=refs[0]['relative_ns'],
                 end_ns=refs[-1]['relative_ns']
                 if event['kind'] == 'interval' else None,
                 endpoint_error_ns=None,
                 temporal_comparison_verified=False))
    unit = dict(provider=proof.provider,
                implementation_sha256=proof.implementation_sha256,
                evidence_ids=list(proof.evidence_ids),
                period_numerator_ns=proof.period_numerator_ns,
                period_denominator=proof.period_denominator,
                max_elapsed_ns=proof.max_elapsed_ns)
    view = dict(
        schema_version=2,
        identity=copy.deepcopy(batch['identity']),
        canonical_sha256=proof.canonical_sha256,
        raw_artifact=batch['raw_artifact'],
        program_coordinates=list(proof.program_coordinates),
        domain_id=proof.domain_id,
        epoch_id=proof.epoch_id,
        observers=chosen,
        origin_tick=origin,
        unit='ns',
        coordinate_system='single_invocation_program_shared_counter_ns',
        clock_status='shared_counter_epoch_precision_unverified',
        counter_epoch_shared=True,
        read_precision_status='unverified',
        physical_temporal_comparison_verified=False,
        time_arrows_verified=False,
        source_boundary_status=batch['boundary_status'],
        unit_proof=unit,
        sources=batch['sources'],
        sites=batch['sites'],
        records=list(projected.values()),
        events=events,
        notes=[
            'One actual invocation/program, one verified counter epoch; every observer uses the same raw origin.',
            'Clock read precision remains unknown; counter coordinates do not certify physical overlap or source costs.',
            'Displayed actual threads are observers, not measured hardware-engine activity.'
        ])
    if proof.scope_kind == 'single_observer':
        view['clock_scope_kind'] = 'single_observer'
        view['observer_epoch_alignment_verified'] = False
        view['notes'].append(
            'One actual observer only; no inter-observer epoch alignment is authorized.'
        )
    if proof.period_uncertainty_numerator_ns:
        unit.update(period_uncertainty_numerator_ns=proof.
                    period_uncertainty_numerator_ns,
                    period_uncertainty_denominator=proof.
                    period_uncertainty_denominator)
        view['notes'].append(
            'Conversion scale error includes the empirical rate interval and rounding; hardware read precision remains unknown.'
        )
    return view


def validate_shared_counter_view(view, canonical, proof):
    expected = derive_shared_counter_view(canonical, proof)
    if type(view) is not dict or view != expected:
        raise ValueError(
            'Shared counter view differs from original canonical/proof projection'
        )
    return expected
