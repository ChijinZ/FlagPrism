"""Derived counter-ns coordinates, separate from immutable raw observations.

Unit evidence does not certify read precision, source-region boundaries or a
shared epoch. These views deliberately grant no temporal-comparison/flow rights.
"""
import copy
from dataclasses import dataclass
import hashlib
import json

from .timeline_clock import TickScale
from .timeline_events import validate_raw_batch, _integer, _sha, _text


def document_sha256(value):
    return hashlib.sha256(
        json.dumps(value,
                   sort_keys=True,
                   separators=(',', ':'),
                   ensure_ascii=False,
                   allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class CounterUnitProof:
    capture_id: str
    invocation_id: str
    binary_id: str
    raw_sha256: str
    observer_id: str
    period_numerator_ns: int
    period_denominator: int
    max_elapsed_ns: int
    provider: str
    evidence_ids: tuple
    implementation_sha256: str | None = None

    def __post_init__(self):
        for field in ('capture_id', 'invocation_id', 'binary_id',
                      'observer_id', 'provider'):
            _text(getattr(self, field), field)
        _sha(self.raw_sha256)
        if self.implementation_sha256 is not None:
            _sha(self.implementation_sha256)
        for field in ('period_numerator_ns', 'period_denominator',
                      'max_elapsed_ns'):
            _integer(getattr(self, field), field, 1)
        if (type(self.evidence_ids) is not tuple or not self.evidence_ids
                or any(
                    type(item) is not str or not item
                    for item in self.evidence_ids)):
            raise ValueError(
                'Counter unit proof requires explicit evidence references')


def derive_counter_ns_views(batch, proofs):
    """One isolated file coordinate per proved observer, with exact floor rules.

    Proofs are provided by a backend, not inferred from event lengths/names.
    Unknown precision stays null rather than becoming a zero-error assertion.
    Missing proofs leave observers raw-only; conflicting supplied proofs fail.
    """
    batch = validate_raw_batch(batch)
    if type(proofs) not in (list, tuple):
        raise ValueError('Expected counter unit proofs')
    observers = {row['id']: row for row in batch['observers']}
    seen, views = set(), []
    for proof in proofs:
        if not isinstance(proof, CounterUnitProof):
            raise TypeError('Counter unit evidence is required')
        if proof.observer_id not in observers or proof.observer_id in seen:
            raise ValueError('Unknown or duplicate observer unit proof')
        seen.add(proof.observer_id)
        if (any(
                getattr(proof, key) != batch['identity'][key]
                for key in ('capture_id', 'invocation_id', 'binary_id'))
                or proof.raw_sha256 != batch['raw_artifact']['sha256']):
            raise ValueError(
                'Counter unit proof is bound to another capture/raw')
        observer = observers[proof.observer_id]
        records = [
            r for r in batch['records']
            if r['observer_id'] == proof.observer_id
        ]
        if not records:
            continue
        origin = min(row['tick'] for row in records)
        maximum = max(row['tick'] for row in records)
        scale = TickScale(proof.period_numerator_ns, proof.period_denominator)
        scale.elapsed_ticks(origin,
                            maximum,
                            bits=observer['timer_bits'],
                            max_elapsed_ns=proof.max_elapsed_ns)
        converted = {}
        for record in records:
            ns, rounding = scale.offset(record['tick'] - origin)
            converted[record['id']] = dict(record,
                                           relative_ns=ns,
                                           conversion_rounding_ns=rounding)
        events = []
        for event in batch['events']:
            if event['observer_id'] != proof.observer_id:
                continue
            refs = [converted[key] for key in event['record_ids']]
            ns = [row['relative_ns'] for row in refs]
            events.append(
                dict(event,
                     start_ns=ns[0],
                     end_ns=ns[-1] if event['kind'] == 'interval' else None,
                     endpoint_error_ns=None,
                     temporal_comparison_verified=False))
        views.append(
            dict(
                schema_version=1,
                identity=copy.deepcopy(batch['identity']),
                canonical_sha256=document_sha256(batch),
                raw_artifact=batch['raw_artifact'],
                observer=observer,
                origin_tick=origin,
                unit='ns',
                coordinate_system='isolated_observer_relative_counter_ns',
                clock_status='counter_unit_only',
                read_precision_status='unverified',
                source_boundary_status=batch['boundary_status'],
                cross_observer_epoch_verified=False,
                time_arrows_verified=False,
                unit_proof=dict(
                    provider=proof.provider,
                    evidence_ids=list(proof.evidence_ids),
                    implementation_sha256=proof.implementation_sha256,
                    period_numerator_ns=proof.period_numerator_ns,
                    period_denominator=proof.period_denominator,
                    max_elapsed_ns=proof.max_elapsed_ns),
                sources=batch['sources'],
                sites=batch['sites'],
                records=list(converted.values()),
                events=events,
                notes=[
                    'These are counter brackets, not certified source-operation costs or engine busy.',
                    'Read precision is unknown; no time arrows or cross-observer comparison are granted.',
                    'Origin is local to this observer/file, without host/device clock correlation.'
                ]))
    return views
