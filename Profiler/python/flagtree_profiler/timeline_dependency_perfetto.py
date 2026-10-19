"""Standard Perfetto exports for backend-qualified observed dependencies."""
import hashlib
from dataclasses import asdict
from pathlib import Path

from . import timeline_perfetto, timeline_dependencies, timeline_store, timeline_shared
from .timeline_dependencies import derive_dependency_view, validate_dependency_view
from .timeline_shared import derive_shared_counter_view
from .timeline_views import document_sha256


def encode_dependency_trace(view,
                            canonical,
                            *,
                            proof,
                            max_bytes=16 * 1024 * 1024):
    view = validate_dependency_view(view, canonical, proof)
    counter = derive_shared_counter_view(canonical, proof.clock)
    leaves = [
        dict(counter,
             observer=observer,
             records=[
                 r for r in counter['records']
                 if r['observer_id'] == observer['id']
             ],
             events=[
                 e for e in counter['events']
                 if e['observer_id'] == observer['id']
             ]) for observer in counter['observers']
    ]
    return timeline_perfetto._encode_counter_views(leaves,
                                                   max_bytes=max_bytes,
                                                   shared=counter,
                                                   dependencies=view)


def write_dependency_exports(directory, canonical, proofs):
    if type(proofs) not in (list, tuple) or len(proofs) > 128:
        raise ValueError('Expected bounded dynamic dependency proof set')
    files = {'canonical.json': timeline_store.json_bytes(canonical)}
    rows, seen, total = [], set(), 0
    for proof in proofs:
        view = derive_dependency_view(canonical, proof)
        domain = view['domain_id']
        if domain in seen:
            raise ValueError('Duplicate dynamic dependency clock scope')
        seen.add(domain)
        payload = encode_dependency_trace(view,
                                          canonical,
                                          proof=proof,
                                          max_bytes=16 * 1024 * 1024 - total)
        total += len(payload)
        view_file, trace_file = 'views/' + domain + '.json', 'traces/' + domain + '.pftrace'
        files[view_file] = timeline_store.json_bytes(view)
        files[trace_file] = payload
        rows.append(
            dict(observer_id=domain,
                 observer_ids=list(proof.clock.observer_ids),
                 invocation_id=proof.clock.invocation_id,
                 program_coordinates=list(proof.clock.program_coordinates),
                 view_file=view_file,
                 trace_file=trace_file,
                 bytes=len(payload),
                 sha256=hashlib.sha256(payload).hexdigest(),
                 clock_status='shared_counter_epoch_precision_unverified',
                 read_precision_status='unverified',
                 time_arrows_verified=True,
                 view_kind='observed_dynamic_dependencies_ns'))
    if not rows:
        return []
    inputs = dict(
        schema_version=3,
        kind='observed_dynamic_dependencies_ns',
        identity=canonical['identity'],
        canonical_sha256=document_sha256(canonical),
        raw_artifact=canonical['raw_artifact'],
        proofs=[
            dict(clock=asdict(p.clock),
                 provider=p.provider,
                 implementation_sha256=p.implementation_sha256,
                 evidence_ids=p.evidence_ids,
                 edges_sha256=document_sha256(list(p.edges))) for p in proofs
        ],
        implementation_sha256={
            Path(m.__file__).name:
            hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
            for m in (timeline_perfetto, timeline_dependencies, timeline_store,
                      timeline_shared)
        },
        perfetto_schema_commit=timeline_perfetto.PERFETTO_SCHEMA_COMMIT)
    with timeline_store.export_lock(directory):
        rows = timeline_store.publish_revision(directory, inputs, files, rows)
        timeline_store.set_dependency_qualification(
            directory, canonical['identity']['invocation_id'], rows)
        timeline_perfetto._write_committed_index(directory)
    return rows
