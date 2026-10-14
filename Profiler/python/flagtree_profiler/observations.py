"""Semantic requests and clock-bounded observations, independent of any SDK.

This contract does not calibrate a clock or establish an association. Producers
must supply their evidence; consumers never infer a join from kernel names or
stretch recorded intervals to a whole-launch duration.
"""
from dataclasses import dataclass
import math
from typing import Optional

SEMANTICS = frozenset({
    'issue',
    'wait_bracket',
    'completion_checkpoint',
    'source_control_interval',
    'native_lifecycle',
    'engine_activity',
    'counter',
    'control_checkpoint',
})
ALIGNMENTS = frozenset({'unverified', 'instance_local', 'verified_shared'})


def _integer(value, name, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


@dataclass(frozen=True)
class ObservationRequest:
    """Select semantic events; occurrence is never assumed to be an iteration."""
    semantics: tuple[str, ...] = ('source_control_interval', )
    programs: Optional[tuple[int, ...]] = (0, )
    sites: Optional[tuple[int, ...]] = None
    max_events_per_instance: int = 256
    sample_every: int = 1

    def __post_init__(self):
        if not isinstance(self.semantics, tuple) or not self.semantics:
            raise ValueError('semantics must be a nonempty tuple')
        if any(s not in SEMANTICS for s in self.semantics):
            raise ValueError('unsupported observation semantics')
        if len(set(self.semantics)) != len(self.semantics):
            raise ValueError('duplicate observation semantics')
        for name in ('programs', 'sites'):
            values = getattr(self, name)
            if values is not None:
                if not isinstance(values, tuple) or not values:
                    raise ValueError(
                        f'{name} must be a nonempty tuple or None')
                for value in values:
                    _integer(value, name)
                if len(set(values)) != len(values):
                    raise ValueError(f'duplicate {name}')
        _integer(self.max_events_per_instance,
                 'max_events_per_instance',
                 minimum=1)
        _integer(self.sample_every, 'sample_every', minimum=1)

    def as_dict(self):
        return {
            'semantics': list(self.semantics),
            'programs': None if self.programs is None else list(self.programs),
            'sites': None if self.sites is None else list(self.sites),
            'max_events_per_instance': self.max_events_per_instance,
            'sample_every': self.sample_every,
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise ValueError('observation request must be an object')
        unknown = set(value) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(
                f'unknown observation request fields: {sorted(unknown)}')
        fields = dict(value)
        for key in ('semantics', 'programs', 'sites'):
            if key in fields and fields[key] is not None:
                if not isinstance(fields[key], (list, tuple)):
                    raise ValueError(f'{key} must be an array')
                fields[key] = tuple(fields[key])
        return cls(**fields)


def validate_clock(value):
    """Validate declared clock evidence without claiming physical verification."""
    if not isinstance(value, dict):
        raise ValueError('clock must be an object')
    clock = dict(value)
    for field in ('domain', 'scope'):
        if not isinstance(clock.get(field), str) or not clock[field]:
            raise ValueError(f'clock requires {field}')
    alignment = clock.get('alignment', 'unverified')
    if alignment not in ALIGNMENTS:
        raise ValueError('invalid clock alignment')
    clock['alignment'] = alignment
    period = clock.get('tick_ns')
    if period is not None and (type(period) not in (int, float)
                               or not math.isfinite(period) or period <= 0):
        raise ValueError('tick_ns must be finite and positive or null')
    if period is not None and not clock.get('conversion_evidence'):
        raise ValueError('clock conversion requires explicit evidence')
    if alignment == 'verified_shared' and not clock.get('alignment_evidence'):
        raise ValueError('shared alignment requires explicit evidence')
    if clock.get('origin_tick') is not None:
        _integer(clock['origin_tick'], 'origin_tick')
    if clock.get('wrap_bits') is not None:
        _integer(clock['wrap_bits'], 'wrap_bits', minimum=1)
        if clock['wrap_bits'] > 64:
            raise ValueError('clock width exceeds 64 bits')
    return clock


def interval_ticks(start, end, clock):
    """Do not infer a wrap from decreasing timestamps without producer evidence."""
    _integer(start, 'start_tick')
    _integer(end, 'end_tick')
    if end >= start:
        return end - start
    bits = clock.get('wrap_bits')
    if bits is None or clock.get('wrap_count') != 1:
        raise ValueError(
            'decreasing timestamps require a verified single wrap')
    limit = 1 << bits
    if start >= limit or end >= limit:
        raise ValueError('timestamp outside declared clock width')
    return limit - start + end


def observation(value):
    """Normalize one event while retaining its measurement and identity scope."""
    if not isinstance(value, dict):
        raise ValueError('observation must be an object')
    result = dict(value)
    for field in ('id', 'source', 'capture_id', 'semantic'):
        if not isinstance(result.get(field), str) or not result[field]:
            raise ValueError(f'observation requires {field}')
    if result['semantic'] not in SEMANTICS:
        raise ValueError('unsupported observation semantic')
    for field in ('program', 'site', 'occurrence', 'iteration', 'buffer_slot'):
        if result.get(field) is not None:
            _integer(result[field], field)
    if result.get('invocation_id') is not None and not isinstance(
            result['invocation_id'], str):
        raise ValueError('invocation_id must be a string or null')
    clock = validate_clock(result['clock']) if result.get('clock') else None
    result['clock'] = clock
    if result.get('start_tick') is not None or result.get(
            'end_tick') is not None:
        if clock is None:
            raise ValueError('timed observations require a clock domain')
        duration = interval_ticks(result['start_tick'], result['end_tick'],
                                  clock)
        result['duration_ticks'] = duration
        period = clock.get('tick_ns')
        result['duration_ns'] = None if period is None else duration * period
        # Relative coordinates only; this never overlays a separate native trace.
        origin = clock.get('origin_tick')
        result['relative_start_ns'] = (
            interval_ticks(origin, result['start_tick'], clock) *
            period if period is not None and origin is not None else None)
    else:
        result['duration_ticks'] = result['duration_ns'] = None
        result['relative_start_ns'] = None
    result.setdefault('association_status', 'unassociated')
    if result['association_status'] not in {
            'verified', 'unassociated', 'ambiguous'
    }:
        raise ValueError('invalid association status')
    if result['association_status'] == 'verified' and (
            not result.get('invocation_id')
            or not result.get('association_evidence')):
        raise ValueError(
            'verified associations require invocation identity and evidence')
    return result


def from_ir_runs(runs):
    """Keep append traces and legacy snapshots distinct; never invent calibration."""
    events = []
    for run_index, run in enumerate(runs):
        events.extend(
            observation(event)
            for event in run.get('semantic_observations', []))
        runtime = run.get('runtime_metadata') or {}
        capture_id = str(
            runtime.get('capture_id') or f'ir-capture-{run_index}')
        supplied_clock = runtime.get('observation_clock')
        clock = supplied_clock or {
            'domain': 'unidentified.device_counter',
            'scope': 'instance_local',
            'alignment': 'unverified',
            'tick_ns': None,
        }
        occurrences = {}
        for record_index, record in enumerate(
            (run.get('decoded') or {}).get('records') or []):
            kind = record.get('record_kind')
            if kind not in ('TIMELINE', 'DYNAMIC_TIMELINE'):
                continue
            dynamic = kind == 'DYNAMIC_TIMELINE'
            key = (record.get('logical_instance_id'), record.get('actor_id'),
                   record.get('op_id'))
            occurrence = occurrences.get(key, 0) if dynamic else None
            if dynamic:
                occurrences[key] = occurrence + 1
            event = {
                'id':
                f'{capture_id}:{"event" if dynamic else "snapshot"}:{record_index}',
                'capture_id':
                capture_id,
                'invocation_id':
                runtime.get('profiler_invocation_id'),
                'association_status':
                ('verified' if runtime.get('profiler_invocation_id')
                 and runtime.get('profiler_association_evidence') else
                 'unassociated'),
                'association_evidence':
                runtime.get('profiler_association_evidence'),
                'source':
                'flagtree_ir_dynamic' if dynamic else 'flagtree_ir_snapshot',
                'semantic':
                'source_control_interval',
                'storage':
                'selected_dynamic_append'
                if dynamic else 'static_site_snapshot',
                'program':
                record.get('logical_instance_id'),
                'site':
                record.get('op_id'),
                'actor':
                record.get('actor_id') if dynamic else None,
                'occurrence':
                occurrence,
                'sequence':
                record.get('sequence') if dynamic else None,
                'attempted_ordinal':
                record.get('attempted_ordinal') if dynamic else None,
                'start_tick':
                record.get('start_cycle'),
                'end_tick':
                record.get('end_cycle'),
                'clock':
                clock,
                'original_record':
                record,
                'limits': ([
                    'Occurrence counts retained events per site; sampling or truncation may omit executions.'
                ] if dynamic else [
                    'Repeated execution of a static site may overwrite this slot.'
                ]) + [
                    'Source control is not engine occupancy or operation completion.'
                ],
            }
            events.append(observation(event))
    return events
