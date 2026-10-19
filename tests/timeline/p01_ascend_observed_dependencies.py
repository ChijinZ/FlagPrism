"""Installed-product checks using real retained native-flag captures only.

No application replay or compiler invocation. Run normal and -O in the server
Docker. This is development contract validation, not independent new mathematics.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from flagtree.profiler.timeline_ascend_native import load_observed_dependency_inputs
from flagtree.profiler.timeline_dependencies import derive_dependency_view
from flagtree.profiler.timeline_dependency_perfetto import encode_dependency_trace


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline',
                        type=Path,
                        action='append',
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    reports, rejected = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, TypeError):
            rejected.append(name)
        else:
            raise RuntimeError('Invalid dependency accepted: ' + name)

    for directory in args.timeline:
        before = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()
        }
        for row in json.loads(
            (directory / 'index.json').read_text())['captures']:
            from flagtree.profiler.timeline_capture_store import load_capture_file
            capture = load_capture_file(directory / row['capture_file'])
            raw = (directory / capture['raw_file']).read_bytes()
            canonical, proofs = load_observed_dependency_inputs(
                directory, capture, raw)
            exports = {
                r['observer_id']: r
                for r in capture['observed_dependency_exports']
            }
            need(
                len(proofs) >= 2,
                'Actual first and last programs are required')
            for proof in proofs:
                view = derive_dependency_view(canonical, proof)
                need(
                    view.get('clock_scope_kind') == 'single_observer'
                    and view.get('observer_epoch_alignment_verified') is False
                    and not view['hardware_busy_qualified']
                    and not view['physical_temporal_comparison_verified'],
                    'Derived view promoted its timing/engine rights')
                saved = exports[proof.clock.domain_id]
                payload = encode_dependency_trace(view, canonical, proof=proof)
                need(
                    payload == (directory / saved['trace_file']).read_bytes(),
                    'Fresh installed export differs from its actual original trace'
                )
                need(
                    view == json.loads(
                        (directory / saved['view_file']).read_text()),
                    'Fresh installed view differs from its original')
                reject(
                    'one_observer_is_not_shared_observers', lambda: replace(
                        proof.clock, scope_kind='shared_observers'))
                reject(
                    'single_scope_cannot_grow',
                    lambda: replace(proof.clock,
                                    observer_ids=proof.clock.observer_ids * 2))
                other = next(
                    p for p in proofs
                    if p.clock.observer_ids != proof.clock.observer_ids)
                foreign = dict(proof.edges[0], target=other.edges[0]['source'])
                reject(
                    'cross_observer_flow', lambda: derive_dependency_view(
                        canonical, replace(proof, edges=(foreign, ))))
                reports.append(
                    dict(invocation_id=row['invocation_id'],
                         domain_id=view['domain_id'],
                         nodes=len(view['nodes']),
                         edges=len(view['edges']),
                         scalar_readiness_checkpoints=sum(
                             e['relation'] ==
                             'native_scalar_wait_readiness_observed'
                             for e in view['edges']),
                         trace_sha256=hashlib.sha256(payload).hexdigest()))
        need(
            before == {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in directory.rglob('*') if p.is_file()
            }, 'Original bundle changed')
    need(reports and any(r['scalar_readiness_checkpoints'] for r in reports),
         'Actual scalar readiness observations are required')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'installed_real_native_dependency_contract_passed_not_full_qualification',
            captures=reports,
            rejections=rejected),
                   indent=2))


if __name__ == '__main__':
    main()
