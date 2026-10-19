"""Check actual retained GCU tag generations; this test never runs a kernel."""
import argparse
import copy
from dataclasses import replace
import json
from pathlib import Path

from flagtree.profiler.timeline_dependencies import derive_dependency_view
from flagtree.profiler.timeline_dependency_perfetto import encode_dependency_trace
from flagtree.profiler.timeline_enflame_dependencies import load_observed_dependency_inputs


def run(timeline, output):
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(timeline / item['capture_file'])
        raw = (timeline / capture['raw_file']).read_bytes()
        canonical, proofs = load_observed_dependency_inputs(
            timeline, capture, raw)
        scopes = []
        for proof in proofs:
            view = derive_dependency_view(canonical, proof)
            evidence = [
                edge['attributes']['backend_evidence']
                for edge in view['edges']
            ]
            if (view.get('clock_scope_kind') != 'single_observer'
                    or not view['time_arrows_verified']
                    or view['hardware_busy_qualified']
                    or not any(row['tag_generation'] >= 1 for row in evidence)
                    or any(row['consumer_readiness_verified']
                           or row['precise_hardware_completion_time_verified']
                           for row in evidence)):
                raise RuntimeError(
                    'Real tag generation scope or semantics differ')
            if (not view['unit_proof']['period_uncertainty_numerator_ns']
                    or any('conversion_scale_error_ns' not in node
                           for node in view['nodes'])):
                raise RuntimeError('Empirical clock uncertainty was lost')
            trace = encode_dependency_trace(view, canonical, proof=proof)
            if not all(name in trace for name in (b'backend_evidence',
                                                  b'conversion_scale_error_ns',
                                                  b'counter_unit_proof')):
                raise RuntimeError(
                    'Perfetto omitted tag/address or clock uncertainty details'
                )
            (output / (view['domain_id'] + '.pftrace')).write_bytes(trace)
            scopes.append(
                dict(program=view['program_coordinates'],
                     edges=len(view['edges']),
                     maximum_tag_generation=max(row['tag_generation']
                                                for row in evidence)))
            try:
                derive_dependency_view(
                    canonical,
                    replace(proof,
                            clock=replace(
                                proof.clock,
                                observer_ids=('another-actual-observer', ))))
            except (ValueError, TypeError, KeyError):
                pass
            else:
                raise RuntimeError('Cross-observer GCU endpoint accepted')
        for name, mutate in [
            ('legacy_address', lambda c: c['metadata']['compiler_metadata'][
                'debug_execution_manifest'].update(
                    buffer_address_encoding='legacy_index_width_unverified')),
            ('another_binary',
             lambda c: c['owner']['function'].update(binary_sha256='0' * 64))
        ]:
            wrong = copy.deepcopy(capture)
            mutate(wrong)
            try:
                load_observed_dependency_inputs(timeline, wrong, raw)
            except (ValueError, TypeError, KeyError):
                pass
            else:
                raise RuntimeError('Invalid retained input accepted: ' + name)
        reports.append(dict(invocation_id=item['invocation_id'],
                            scopes=scopes))
    if not reports:
        raise RuntimeError('No actual captures were tested')
    (output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'retained_real_GCU_observed_tag_generations_passed_not_device_or_UI_qualification',
            application_replayed=False,
            captures=reports),
                   indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.timeline, args.output)
