"""Observed dynamic dependencies on actual shared-counter record endpoints.

Backend mappers establish mechanism semantics. This common layer checks identity,
clock scope, exact endpoint projection, acyclicity and observed counter order.
It does not infer engine activity, physical overlap or a completion instant.
"""
import copy
import heapq
from dataclasses import dataclass

from .timeline_events import _text, _sha, stable_id
from .timeline_shared import SharedCounterProof, derive_shared_counter_view
from .timeline_views import document_sha256


@dataclass(frozen=True)
class ObservedDependencyProof:
    clock: SharedCounterProof
    provider: str
    implementation_sha256: str
    evidence_ids: tuple
    edges: tuple

    def __post_init__(self):
        if not isinstance(self.clock, SharedCounterProof):
            raise TypeError(
                'Observed dependencies require a scoped clock proof')
        _text(self.provider, 'dependency provider')
        _sha(self.implementation_sha256)
        if type(self.evidence_ids) is not tuple or not self.evidence_ids:
            raise ValueError('Dynamic dependencies require mechanism evidence')
        for value in self.evidence_ids:
            _text(value, 'mechanism evidence ID')
        if type(self.edges) is not tuple or not 1 <= len(self.edges) <= 100000:
            raise ValueError(
                'Expected bounded nonempty dynamic dependency set')


def derive_dependency_view(canonical, proof):
    if not isinstance(proof, ObservedDependencyProof):
        raise TypeError(
            'Obtain dynamic dependency proof from its backend mapper')
    counter = derive_shared_counter_view(canonical, proof.clock)
    records = {r['id']: r for r in counter['records']}
    sites = {s['id']: s for s in counter['sites']}
    sources = {s['id']: s for s in counter['sources']}
    event_by_record = {}
    for event in counter['events']:
        for record in event['record_ids']:
            if record in event_by_record:
                raise ValueError(
                    'Dependency endpoint has ambiguous event membership')
            event_by_record[record] = event
    nodes, edges, keys = {}, [], set()
    for supplied in proof.edges:
        if type(supplied) is not dict or set(supplied) != {
                'source', 'target', 'relation', 'association_key',
                'display_label', 'attributes'
        }:
            raise ValueError('Unknown dynamic dependency edge schema')
        source, target = supplied['source'], supplied['target']
        if source == target or source not in records or target not in records:
            raise ValueError(
                'Dependency endpoint absent from its actual clock scope')
        for name in ('relation', 'association_key', 'display_label'):
            _text(supplied[name], 'dependency ' + name)
        if type(supplied['attributes']) is not dict:
            raise ValueError('Dynamic dependency attributes must be a mapping')
        # Validate JSON primitives/size without granting any backend-specific
        # interpretation to these descriptive attributes.
        if len(str(supplied['attributes'])) > 65536:
            raise ValueError(
                'Dynamic dependency attributes exceed display budget')
        document_sha256(supplied['attributes'])
        key = source, target, supplied['relation'], supplied['association_key']
        if key in keys:
            raise ValueError('Duplicate dynamic dependency edge')
        keys.add(key)
        if records[source]['relative_ns'] > records[target]['relative_ns']:
            raise ValueError(
                'Observed counter endpoints reverse the dynamic dependency')
        for record_id in (source, target):
            record, event = records[record_id], event_by_record[record_id]
            nodes[record_id] = dict(
                id=record_id,
                observer_id=record['observer_id'],
                event_id=event['id'],
                site_id=event['site_id'],
                label=sites[event['site_id']]['name'] + ' / ' +
                record['phase'],
                source_locations=[
                    sources[key]['location']
                    for key in sites[event['site_id']]['source_ids']
                ],
                phase=record['phase'],
                time_ns=record['relative_ns'],
                tick=record['tick'],
                raw_offset=record['offset'],
                raw_length=record['length'],
                occurrence=event['occurrence'],
                coverage=copy.deepcopy(event['coverage']))
        edges.append(
            dict(id=stable_id(
                tuple(counter['identity'][k]
                      for k in ('capture_id', 'invocation_id', 'binary_id')),
                'observed-dependency', *key),
                 **copy.deepcopy(supplied)))
    incoming = {key: 0 for key in nodes}
    outgoing = {key: [] for key in nodes}
    for edge in edges:
        incoming[edge['target']] += 1
        outgoing[edge['source']].append(edge['target'])
    ready = [(nodes[key]['time_ns'], key) for key, degree in incoming.items()
             if not degree]
    heapq.heapify(ready)
    order = []
    while ready:
        _, key = heapq.heappop(ready)
        order.append(key)
        for target in outgoing[key]:
            incoming[target] -= 1
            if incoming[target] == 0:
                heapq.heappush(ready, (nodes[target]['time_ns'], target))
    if len(order) != len(nodes):
        raise ValueError('Dynamic dependencies contain a cycle')
    for rank, key in enumerate(order):
        nodes[key]['topological_rank'] = rank
    return dict(
        schema_version=1,
        kind='observed_dynamic_dependencies_ns',
        identity=copy.deepcopy(counter['identity']),
        raw_artifact=counter['raw_artifact'],
        canonical_sha256=counter['canonical_sha256'],
        counter_view_sha256=document_sha256(counter),
        domain_id=counter['domain_id'],
        epoch_id=counter['epoch_id'],
        program_coordinates=counter['program_coordinates'],
        unit='ns',
        origin_tick=counter['origin_tick'],
        nodes=[nodes[key] for key in order],
        edges=sorted(edges, key=lambda r: r['id']),
        provider=proof.provider,
        implementation_sha256=proof.implementation_sha256,
        evidence_ids=list(proof.evidence_ids),
        time_arrows_verified=True,
        read_precision_status='unverified',
        physical_temporal_comparison_verified=False,
        source_cost_qualified=False,
        hardware_busy_qualified=False,
        notes=[
            'Arrows connect actual observed record endpoints using backend-verified dynamic identities.',
            'Wait return and consumer issue observations are not physical engine completion or busy intervals.',
            'Only the selected actual observers are displayed; participation checks remain backend evidence.'
        ])


def validate_dependency_view(view, canonical, proof):
    expected = derive_dependency_view(canonical, proof)
    if type(view) is not dict or view != expected:
        raise ValueError(
            'Dynamic dependency view differs from its actual inputs/proof')
    return expected
