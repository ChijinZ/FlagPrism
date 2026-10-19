"""Actual full-width samples on one common CTA axis; no physical overlap grant."""
import argparse
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import struct


def need(value, message):
    if not value:
        raise RuntimeError(message)


def run(timeline,
        output,
        *,
        provider,
        shared,
        codec,
        units,
        adapter,
        require_default=False):
    output.mkdir(parents=True)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    folder = output / 'timeline'
    shutil.copytree(timeline, folder)
    reports, denied, exports = [], [], []

    def reject(label, action):
        try:
            action()
        except (ValueError, TypeError) as error:
            denied.append(dict(case=label, reason=str(error)))
        else:
            raise RuntimeError('Invalid shared scope accepted: ' + label)

    for item in json.loads((folder / 'index.json').read_text())['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(folder / item['capture_file'])
        raw = (folder / capture['raw_file']).read_bytes()
        if require_default:
            need(
                capture.get('shared_counter_status', {}).get('status')
                == 'shared_counter_epoch_precision_unverified'
                and len(capture.get('shared_counter_exports', [])) == 2,
                'Actual default capture did not publish both shared program traces'
            )
        need(
            hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
            'Actual raw changed')
        batch, proofs = provider.load_shared_counter_inputs(
            folder, capture, raw)
        need(len(proofs) == 2, 'Expected both actual selected programs')
        for proof in proofs:
            view = shared.derive_shared_counter_view(batch, proof)
            need([
                o['attributes']['nvidia.thread_flat_index']
                for o in view['observers']
            ] == [0, 32, 64, 96],
                 'Shared view did not select actual distinct-warp threads')
            for record in view['records']:
                need(
                    struct.unpack_from('<Q', raw,
                                       record['offset'])[0] == record['tick'],
                    'Shared record aliases raw field')
                need(
                    record['relative_ns'] == record['tick'] -
                    view['origin_tick'],
                    'Observer independently zeroed or shifted')
            need(
                not view['physical_temporal_comparison_verified']
                and not view['time_arrows_verified'],
                'Counter epoch falsely grants physical precision or flows')
            reject(
                'different_invocation',
                lambda: shared.derive_shared_counter_view(
                    batch, replace(proof, invocation_id='other-invocation')))
            reject(
                'changed_canonical', lambda: shared.derive_shared_counter_view(
                    batch, replace(proof, canonical_sha256='0' * 64)))
            other = next(p for p in proofs
                         if p.program_coordinates != proof.program_coordinates)
            mixed = (proof.observer_ids[0], other.observer_ids[0])
            reject(
                'cross_program_observers',
                lambda: shared.derive_shared_counter_view(
                    batch, replace(proof, observer_ids=mixed)))
            altered = copy.deepcopy(view)
            altered['records'][0]['relative_ns'] += 1
            reject(
                'forged_shared_coordinate', lambda: codec.
                encode_shared_counter_trace(altered, batch, proof=proof))
            altered = copy.deepcopy(view)
            altered['time_arrows_verified'] = True
            reject(
                'forged_time_flow_rights', lambda: codec.
                encode_shared_counter_trace(altered, batch, proof=proof))
            reports.append(
                dict(invocation=proof.invocation_id,
                     program=list(proof.program_coordinates),
                     observers=len(view['observers']),
                     events=len(view['events']),
                     first_ns_by_observer={
                         o['local_id']:
                         min(r['relative_ns'] for r in view['records']
                             if r['observer_id'] == o['id'])
                         for o in view['observers']
                     }))
        incomplete = copy.deepcopy(batch)
        incomplete['complete'] = False
        p = replace(proofs[0],
                    canonical_sha256=shared.document_sha256(incomplete))
        reject('capture_loss',
               lambda: shared.derive_shared_counter_view(incomplete, p))
        wrong = copy.deepcopy(capture)
        wrong['owner']['layout']['num_ctas'] = True
        reject('boolean_native_geometry',
               lambda: provider.load_shared_counter_inputs(folder, wrong, raw))
        rows = codec.write_shared_counter_exports(folder, batch, proofs)
        need(
            codec.write_shared_counter_exports(folder, batch, proofs) == rows,
            'Shared revision is not idempotent')
        for row in rows:
            exports.append(
                dict(row,
                     view_file=str(folder / row['view_file']),
                     trace_file=str(folder / row['trace_file']),
                     fixture=False))
        # The refactored common renderer must preserve original isolated bytes.
        old = adapter.canonicalize_late_capture(raw,
                                                owner=capture['owner'],
                                                metadata=capture['metadata'])
        unit_proofs = units.load_late_counter_unit_proofs(folder, capture, old)
        lookup = {p.observer_id: p for p in unit_proofs}
        for row in capture['counter_ns_exports']:
            v = json.loads((folder / row['view_file']).read_text())
            need(
                codec.encode_counter_trace(
                    v, old, proof=lookup[row['observer_id']]) == (
                        folder / row['trace_file']).read_bytes(),
                'Legacy isolated trace bytes changed during shared refactoring'
            )
    for file, digest in original.items():
        need(
            hashlib.sha256(Path(file).read_bytes()).hexdigest() == digest,
            'Private original modified')
    (output / 'manifest.json').write_text(json.dumps(exports, indent=2) + '\n')
    result = dict(
        status=
        'actual_distinct_warp_shared_counter_coordinates_and_legacy_bytes_passed_not_physical_precision_or_flows',
        actual=reports,
        negative_cases=denied,
        shared_traces=len(exports),
        original_files_unchanged=len(original),
        application_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--require-default', action='store_true')
    a = p.parse_args()
    from flagtree.profiler import timeline_nvidia_shared as provider, timeline_shared as shared
    from flagtree.profiler import timeline_perfetto as codec, timeline_unit_nvidia_late as units
    from flagtree.profiler import timeline_events_nvidia_late as adapter
    run(a.timeline,
        a.output,
        provider=provider,
        shared=shared,
        codec=codec,
        units=units,
        adapter=adapter,
        require_default=a.require_default)


if __name__ == '__main__': main()
