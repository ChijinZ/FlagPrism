"""Real raw async byte-model contracts; mutations are CPU fixtures only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
from flagtree.profiler.timeline_nvidia_late_raw import decode_late_raw
from flagtree.profiler.timeline_nvidia_late_async import derive_late_async


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    index = json.loads((a.timeline / 'index.json').read_text())
    inputs, results, negatives = {}, [], []
    for item in index['captures']:
        capture = json.loads((a.timeline / item['capture_file']).read_text())
        path = a.timeline / capture['raw_file']
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != capture['raw_sha256']:
            raise RuntimeError('Actual retained raw hash changed')
        inputs[str(path)] = digest
        plan, layout = capture['owner']['plan'], capture['owner']['layout']
        decoded = decode_late_raw(plan, raw, slots=layout['slots'])
        shared = capture['metadata']['compiler_metadata']['shared']
        report = derive_late_async(decoded, plan, shared_bytes=shared)
        if report['status'] != 'dynamic_byte_model_consistent':
            raise RuntimeError('Actual positive byte model failed: ' +
                               str(report))
        results.append(
            dict(raw_sha256=digest,
                 programs=len(report['programs']),
                 groups=[p['commit_groups'] for p in report['programs']]))
    # Last actual runtime-K capture exercises steady-state generations. Never
    # write fixture modifications back into any captured file or export a trace.
    words = list(struct.unpack('<' + str(len(raw) // 8) + 'Q', raw))
    actors = plan['actors']
    stream = decoded['programs'][0]['observers'][0]['events']
    wait = next(i for i, e in enumerate(stream) if e['kind'] == 'wait_bracket')
    barrier = next(i for i in range(wait + 1, len(stream))
                   if stream[i]['kind'] == 'cta_barrier_after')
    matrix = next(site['site_id'] for site in plan['sites']
                  if site['kind'] == 'matrix_issue_bracket')
    for case in ('invalid_wait_operand', 'missing_wait',
                 'missing_publication_barrier', 'divergent_participants'):
        changed = words.copy()
        for actor in range(actors if case != 'divergent_participants' else 1):
            row = 6 + 4 * (barrier
                           if case == 'missing_publication_barrier' else wait)
            if case == 'invalid_wait_operand':
                changed[(row + 3) * actors + actor] = 9
            else:
                changed[row * actors + actor] = matrix
        fixture = struct.pack('<' + str(len(changed)) + 'Q', *changed)
        fixture_decoded = decode_late_raw(plan, fixture, slots=layout['slots'])
        report = derive_late_async(fixture_decoded, plan, shared_bytes=shared)
        expected = 'model_unavailable' if case == 'divergent_participants' else 'model_inconsistent'
        if report['status'] != expected or report['time_flows_qualified']:
            raise RuntimeError('Unsafe async fixture accepted: ' + case + ' ' +
                               str(report))
        negatives.append(
            dict(case=case, status=report['status'], reason=report['reason']))
    for case in ('opaque_native', 'partial_footprint',
                 'unknown_ldmatrix_geometry'):
        fixture = copy.deepcopy(plan)
        if case == 'opaque_native':
            next(site for site in fixture['sites'] if site['kind'] ==
                 'copy_submit_after')['kind'] = 'opaque_native_issue_bracket'
        elif case == 'partial_footprint':
            fixture['dependency_footprint_complete'] = False
        else:
            next(
                site for site in fixture['sites']
                if site['kind'] == 'shared_load_issue_bracket'
            )['members'][0][
                'native_operation'] = 'llvm.nvvm.ldmatrix.sync.aligned.m8n8.x1.b16.p3'
        report = derive_late_async(decoded, fixture, shared_bytes=shared)
        if report['status'] != 'model_unavailable' or report[
                'time_flows_qualified']:
            raise RuntimeError(
                'Unmodeled native semantics were granted dependency qualification'
            )
        negatives.append(
            dict(case=case, status=report['status'], reason=report['reason']))
    for path, expected in inputs.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Original raw was modified')
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_raw_byte_model_and_negative_cpu_fixtures_passed_no_device_replay',
            inputs=inputs,
            actual=results,
            negative_fixtures_only=negatives),
                   indent=2))


if __name__ == '__main__':
    main()
