"""Black-box verifier of the documented public automatic-capture schema.

Run ONLY in server Docker. No profiler import, private API, site selection,
LLVM transformation, or numerical reference is implemented here. Math is checked
by the unchanged ordinary workload before it writes its independent receipt.
"""
import argparse
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import math
from pathlib import Path


class ContractError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def preserves(actual, original):
    if isinstance(original, dict):
        return isinstance(actual, dict) and all(key in actual and preserves(actual[key], value) for key, value in original.items())
    if isinstance(original, list):
        return isinstance(actual, list) and len(actual) == len(original) and all(preserves(a, b) for a, b in zip(actual, original))
    return actual == original


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def inside(bundle, relative):
    require(isinstance(relative, str), 'artifact reference is not a string')
    path = (bundle / relative).resolve()
    require(path.is_relative_to(bundle.resolve()), f'artifact escapes bundle: {relative}')
    require(path.is_file(), f'missing referenced artifact: {relative}')
    return path


def verify_manifest(bundle):
    manifest = load(bundle / 'manifest.json')
    files = manifest.get('files')
    require(isinstance(files, dict) and files, 'manifest.files must be a nonempty mapping')
    for relative, info in files.items():
        path = inside(bundle, relative)
        require(integer(info.get('bytes')) and path.stat().st_size == info['bytes'], f'manifest byte mismatch: {relative}')
        require(digest(path) == info.get('sha256'), f'manifest hash mismatch: {relative}')
    actual = {str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file() and p != bundle / 'manifest.json'}
    require(actual == set(files), 'manifest does not cover exact complete bundle file set')
    total = sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file())
    require(total <= 64 * 1024 * 1024, f'complete bundle exceeds64MiB: {total}')
    require(any(path.startswith('raw/') for path in files), 'no retained raw evidence in bundle')
    return {'files_verified': len(files), 'complete_bundle_bytes': total}


def verify_clock(record):
    clock = record['clock']
    ticks = [record[key] for key in ['start_tick', 'end_tick', 'duration_ticks']]
    for value in ticks:
        require(value is None or integer(value), 'noninteger device ticks')
    for key in ['duration_ns', 'relative_start_ns']:
        require(record[key] is None or number(record[key]), f'invalid {key}')
    if clock is None:
        require(all(value is None for value in ticks) and record['duration_ns'] is None
                and record['relative_start_ns'] is None, 'timestamps without clock evidence')
        return
    require(isinstance(clock, dict), 'clock must be object or null')
    for key in ['domain', 'scope', 'alignment']:
        require(isinstance(clock.get(key), str) and clock[key], f'missing clock.{key}')
    tick_ns = clock.get('tick_ns')
    require(tick_ns is None or number(tick_ns) and tick_ns > 0, 'invalid tick period')
    if clock['alignment'] == 'verified_shared':
        require(bool(clock.get('alignment_evidence')), 'shared clock lacks alignment evidence')
    start, end, duration = ticks
    require(duration is None or duration >= 0, 'negative counter duration')
    if start is not None and end is not None:
        require(end >= start, 'counter wrap/decrease requires a separately documented decoder check')
    if start is not None and end is not None and duration is not None and end >= start:
        require(duration == end - start, 'duration_ticks does not match retained counters')
    if record['duration_ns'] is not None:
        require(tick_ns is not None and duration is not None, 'duration conversion lacks ticks/period')
        require(math.isclose(record['duration_ns'], duration * tick_ns, rel_tol=1e-8, abs_tol=1e-6), 'duration conversion mismatch')
    if record['relative_start_ns'] is not None:
        require(clock.get('origin_tick') is not None or bool(clock.get('alignment_evidence')),
                'relative start lacks origin/alignment evidence')


def verify_loss(capture, backend):
    if backend == 'nvidia':
        decoded = capture.get('decoded', {})
        losses = decoded.get('losses')
        require(isinstance(losses, list) and losses, 'missing NVIDIA primitive loss rows')
        require(decoded.get('unpaired_records') == [], 'unpaired NVIDIA entry/exit records')
        require(decoded.get('dropped_records') == 0, 'NVIDIA aggregate drop or unknown loss')
        retained = 0
        for row in losses:
            for key in ['program', 'sm', 'warp', 'written_records', 'retained_records', 'dropped_records', 'capacity_records']:
                require(integer(row.get(key)) and row[key] >= 0, f'invalid NVIDIA loss.{key}')
            require(row['written_records'] == row['retained_records'] + row['dropped_records'], 'NVIDIA primitive accounting mismatch')
            require(row['retained_records'] <= row['capacity_records'], 'NVIDIA retained capacity exceeded')
            require(row['dropped_records'] == 0, 'NVIDIA default lost primitive records')
            retained += row['retained_records']
        require(retained > 0, 'empty NVIDIA device capture')
        return {'primitive_records_retained': retained, 'dropped': 0}
    require(capture.get('capture_status') == 'decoded', 'backend capture not decoded')
    require(capture.get('decode_error') is None, 'backend capture decode error')
    require(capture.get('counter_saturated') is False, 'saturated or unknown device counter')
    if backend == 'ascend':
        actors = capture.get('actors')
        require(isinstance(actors, list) and actors, 'missing Ascend actor accounting')
        committed = 0
        dropped = 0
        for actor in actors:
            for key in ['attempted', 'committed', 'dropped']:
                require(integer(actor.get(key)) and actor[key] >= 0, f'invalid Ascend actor.{key}')
            require(actor['attempted'] == actor['committed'] + actor['dropped'], 'Ascend actor accounting mismatch')
            require(actor['dropped'] == 0, 'Ascend default lost device records')
            if actor.get('state') == 'no_records':
                require(actor.get('execution_status') == 'unknown', 'empty actor falsely classified as unexecuted')
            committed += actor['committed']
            dropped += actor['dropped']
        require(capture.get('dropped') == dropped and committed > 0, 'invalid/empty Ascend aggregate accounting')
        return {'dynamic_records_committed': committed, 'dropped': dropped}
    require(capture.get('record_layout') == 'selected_dynamic_timeline_v1', 'GCU default is not dynamic-visit protocol')
    header = capture.get('header', {})
    for key in ['write_idx', 'capacity', 'overflow_count', 'flags', 'reserved0']:
        require(integer(header.get(key)) and header[key] >= 0, f'invalid GCU header.{key}')
    require(header['capacity'] > 0, 'empty GCU capacity')
    require(header['reserved0'] >= header['write_idx'], 'GCU sampling accounting inconsistent')
    require(header['overflow_count'] == max(0, header['write_idx'] - header['capacity']), 'GCU overflow arithmetic mismatch')
    require(not header['flags'] & 17 and header['overflow_count'] == 0, 'GCU overflow/saturation')
    require(header['reserved0'] == header['write_idx'], 'default qualification temporally sampled visits; exact loop count unavailable')
    require(header['write_idx'] > 0, 'empty GCU dynamic capture')
    return {'attempted_before_sampling': header['reserved0'], 'sampled_publication_attempts': header['write_idx'],
            'retained': min(header['write_idx'], header['capacity']), 'overflow': 0, 'sampling_omissions': 0}


def verify_plans(document, backend, binary_ids):
    require(document.get('schema_version') == 1, 'plan envelope major version')
    require(isinstance(document.get('capture_evidence'), list), 'missing plan capture evidence')
    plans = document.get('plans')
    require(isinstance(plans, list) and plans, 'no automatic inventory/plan')
    selected_by_binary = {binary: set() for binary in binary_ids}
    summaries = []
    for entry in plans:
        if entry.get('binary_id') not in binary_ids:
            continue
        plan = entry.get('plan', {})
        inventory = plan.get('inventory')
        require(isinstance(inventory, list) and inventory, 'missing actual compiler candidate inventory')
        require(isinstance(plan.get('policy'), str) and plan['policy'], 'missing automatic policy')
        require(integer(plan.get('max_sites')) and plan['max_sites'] > 0, 'missing bounded site budget')
        require(all(isinstance(item.get('selected'), bool) for item in inventory), 'inventory selection flags missing')
        selected = [item for item in inventory if item['selected']]
        require(selected and all(isinstance(item.get('selection_reason'), str) and item['selection_reason'] for item in selected), 'selection reasons missing')
        require(len(selected) <= plan['max_sites'], 'automatic site budget exceeded')
        if backend == 'nvidia':
            require(plan.get('schema_version') == 2, 'NVIDIA count-only plan is not full-inventory qualification')
            require(plan.get('proton.automatic_candidates') == len(inventory), 'NVIDIA actual candidate count mismatch')
            require(plan.get('proton.automatic_selected') == len(selected), 'NVIDIA actual selected count mismatch')
            for item in inventory:
                require(integer(item.get('candidate_ordinal')), 'missing NVIDIA inventory ordinal')
                require(isinstance(item.get('operation'), str) and item['operation'], 'missing NVIDIA operation')
                require(isinstance(item.get('location'), dict), 'missing structured NVIDIA location')
                require(isinstance(item.get('candidate_class'), str), 'missing NVIDIA candidate class')
            sites = [item.get('scope_id') for item in selected if integer(item.get('scope_id'))]
        else:
            candidates = plan.get('candidate_count')
            require(integer(candidates) and len(selected) <= candidates <= len(inventory), 'actual candidate inventory/count mismatch')
            if backend == 'ascend':
                require(plan.get('selected_count') == len(selected), 'Ascend selected count mismatch')
                sites = [item.get('site_id') for item in selected]
            else:
                require(plan.get('schema_version') == 1, 'GCU automatic plan schema')
                sites = plan.get('selected_sites')
                require(isinstance(sites, list), 'missing GCU selected sites')
                from_inventory = [item.get('opId', item.get('op_id')) for item in selected]
                require(set(sites) == set(from_inventory), 'GCU selection not bound to actual inventory')
                for item in inventory:
                    require(isinstance(item.get('automatic_eligible'), bool), 'GCU eligibility field missing')
                    if not item['automatic_eligible']:
                        require(bool(item.get('exclusion_reason')), 'GCU excluded IR bookkeeping lacks reason')
        require(all(integer(site) and site >= 0 for site in sites), 'invalid actual selected site')
        selected_by_binary[entry['binary_id']].update(sites)
        summaries.append({'binary_id': entry['binary_id'], 'candidate_count': len(inventory), 'selected_count': len(selected)})
    require(all(sites for sites in selected_by_binary.values()), 'binary has no actual selected-site plan')
    return selected_by_binary, summaries


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for key, value in attrs if key == 'href' and value)


def verify_report(bundle, records):
    index = bundle / 'report' / 'index.html'
    view = bundle / 'report' / 'fine_grained.html'
    require(index.is_file() and view.is_file(), 'missing source-linked user report')
    links = Links()
    links.feed(index.read_text())
    require(any((index.parent / href.split('#', 1)[0]).resolve() == view.resolve() for href in links.hrefs), 'main report does not link internal source view')
    content = unescape(view.read_text())
    for row in records:
        require(row['invocation_id'] in content and str(row['binary_id']) in content, 'report omits actual call/binary identity')
    require(any(Path(loc['file']).name in content for row in records for loc in row['source_locations']), 'report omits source locations')
    return {'main_to_internal_link': True, 'source_and_actual_identity_visible_in_html': True,
            'interactive_browser_controls': 'not_executed_by_this_file_verifier'}


def verify(bundle, receipt_path, cohort_path, backend, case, si, ci):
    cohort = load(cohort_path)
    rows = cohort['backend_evidence'][backend]['runtime_probe' if case == 'runtime_recurrence' else 'common_combinations']
    baseline = next(row for row in rows if (row['case'], row['shape_index'], row['config_index']) == (case, si, ci))
    receipt = load(receipt_path)
    for key in ['case', 'shape_index', 'config_index', 'shape', 'config', 'grid', 'input_sha256']:
        require(receipt.get(key) == baseline[key], f'candidate changed frozen workload {key}')
    require(len(receipt['calls']) == len(baseline['calls']), 'requested user-call count changed')
    for actual, original in zip(receipt['calls'], baseline['calls']):
        for key in ['atol', 'rtol', 'runtime_steps']:
            require(actual.get(key) == original.get(key), f'original numerical/loop oracle changed: {key}')
        require(actual.get('input_unchanged') is True and actual.get('canaries') is True, 'original math/input/canary receipt incomplete')
    if 'output_initial_sha256' in baseline:
        require(receipt.get('output_initial_sha256') == baseline['output_initial_sha256'], 'non-idempotent output seed changed')
        require(receipt.get('non_idempotence_witness_max_abs') == baseline['non_idempotence_witness_max_abs'], 'replay witness input changed')
    metrics = verify_manifest(bundle)
    fine = load(bundle / 'ai' / 'fine_grained.json')
    original = load(bundle / 'ai' / 'observations.json')
    for data in [fine, original]:
        require(data.get('schema_version') == 1, 'observation envelope major version')
        require(isinstance(data.get('captures'), list), 'capture evidence missing')
    require(fine.get('status') == 'dynamic_records_available', 'no actual internal dynamic records')
    require(isinstance(original.get('observations'), list) and original['observations'], 'no original device observations')
    require(isinstance(fine.get('limits'), list) and isinstance(fine.get('rejected'), list), 'missing coverage/rejected evidence')
    binaries = load(bundle / 'ai' / 'binaries.json')
    launches = load(bundle / 'ai' / 'launches.json')
    require(isinstance(binaries, list) and isinstance(launches, list), 'binary/launch public schema is top-level arrays')
    binary_map = {row['id']: row for row in binaries}
    launch_map = {row['id']: row for row in launches}
    require(len(launch_map) == len(launches), 'duplicate launch identity')
    expected_hashes = {call['compiled_kernel_hash'] for call in receipt['calls']}
    require(None not in expected_hashes and '' not in expected_hashes, 'actual compiled identity absent in user receipt')
    specification = next((row for row in cohort['cases'] if row['case'] == case), None)
    expected_source = specification['source'] if specification else 'kernels.py'
    function_regions = {}
    for binary_id in expected_hashes:
        require(binary_id in binary_map, 'actual CompiledKernel.hash not present in public binary inventory')
        binary = binary_map[binary_id]
        require(binary.get('identity') == 'compiler_cache_hash', 'binary identity is not actual compiler cache hash')
        require(isinstance(binary.get('binary_sha256'), str) and len(binary['binary_sha256']) == 64, 'missing actual device binary digest')
        source = binary.get('source', {})
        filename = Path(source.get('path', '')).name
        require(filename == expected_source, 'binary is not from the expected mathematical source')
        require(source.get('file_sha256') == cohort['source_sha256'][filename], 'captured full source changed')
        snapshot = inside(bundle, source.get('file_snapshot_file'))
        require(digest(snapshot) == source['file_sha256'], 'source snapshot mismatch')
        lines = snapshot.read_text().splitlines()
        start = next(i for i, line in enumerate(lines, 1) if line.startswith(f'def {case}('))
        end = next((i for i in range(start + 1, len(lines) + 1) if lines[i - 1].startswith('def ')), len(lines) + 1)
        function_regions[binary_id] = (start, end)
        require(digest(inside(bundle, source.get('text_file'))) == source.get('sha256'), 'JIT source text mismatch')
        artifacts = binary.get('compiler_artifact_files')
        require(isinstance(artifacts, dict) and artifacts, 'missing retained actual compiler stages')
        for artifact in artifacts.values():
            path = inside(bundle, artifact.get('file'))
            require(path.stat().st_size == artifact.get('bytes') and digest(path) == artifact.get('sha256'), 'compiled artifact mismatch')
    required = ['id', 'capture_id', 'invocation_id', 'binary_id', 'program', 'actor', 'site', 'semantic',
                'occurrence', 'iteration', 'source_locations', 'operation', 'association_status', 'source_status',
                'association_evidence', 'native_event_ids', 'clock', 'start_tick', 'end_tick', 'duration_ticks',
                'duration_ns', 'relative_start_ns', 'unit', 'truncated', 'sampling']
    records = []
    partial_records = 0
    seen_record_ids = set()
    for row in fine.get('records', []):
        require(all(key in row for key in required), 'normalized record missing documented keys')
        if row['binary_id'] not in expected_hashes or row['semantic'] == 'native_lifecycle':
            continue
        require(isinstance(row['id'], str) and row['id'] and row['id'] not in seen_record_ids, 'duplicate/invalid device record identity')
        seen_record_ids.add(row['id'])
        require(isinstance(row['capture_id'], str) and row['capture_id'], 'invalid original capture identity')
        if row['association_status'] != 'verified' or row['source_status'] != 'located':
            partial_records += 1
            continue
        require(row['invocation_id'] in launch_map, 'record call not in actual launch inventory')
        require(launch_map[row['invocation_id']]['binary_id'] == row['binary_id'], 'call/binary association crosses instances')
        if any(row[key] is None for key in ['program', 'actor', 'site', 'occurrence', 'operation']):
            partial_records += 1
            continue
        require(integer(row['program']) and row['program'] >= 0, 'invalid real program identity')
        require(integer(row['site']) and row['site'] >= 0 and integer(row['occurrence']) and row['occurrence'] >= 0, 'invalid site/visit identity')
        require(isinstance(row['operation'], str) and row['operation'] and isinstance(row['semantic'], str) and row['semantic'], 'anonymous internal operation/semantics')
        require(row['truncated'] is not True, 'truncated default internal record')
        source = binary_map[row['binary_id']]['source']
        start, end = function_regions[row['binary_id']]
        valid = [loc for loc in row['source_locations'] if loc.get('file') == source['path'] and integer(loc.get('line'))
                 and start <= loc['line'] < end]
        if not valid:
            partial_records += 1
            continue
        verify_clock(row)
        records.append(row)
    require(records, 'static/native-only or empty capture')
    require(not partial_records or fine['limits'], 'partial source/identity coverage has no interpretation limits')
    invocations = {row['invocation_id'] for row in records}
    require(len(invocations) == len(receipt['calls']), 'source-linked invocation count differs from ordinary requests')
    for invocation in invocations:
        rows = [row for row in records if row['invocation_id'] == invocation]
        require(len({row['site'] for row in rows}) >= 2, 'fewer than two internal device sites per invocation')
        positions = {(loc['file'], loc['line']) for row in rows for loc in row['source_locations']
                     if loc['file'] == binary_map[row['binary_id']]['source']['path']
                     and function_regions[row['binary_id']][0] <= loc['line'] < function_regions[row['binary_id']][1]}
        require(len(positions) >= 2, 'internal sites do not distinguish source positions')
    plan = load(bundle / 'ai' / 'observation_plan.json')
    selected, plan_summary = verify_plans(plan, backend, expected_hashes)
    require(all(row['site'] in selected[row['binary_id']] for row in records), 'dynamic site not selected in actual binary plan')
    capture_map = {row.get('capture_id'): row for row in original['captures'] if row.get('capture_id') is not None}
    losses = {}
    for cid in {row['capture_id'] for row in records}:
        require(cid in capture_map, 'dynamic record has no original capture')
        losses[cid] = verify_loss(capture_map[cid], backend)
        require(any(preserves(row, capture_map[cid]) for row in fine['captures']), 'normalized capture evidence changed')
        require(any(preserves(row, capture_map[cid]) for row in plan['capture_evidence']), 'plan capture evidence changed')
    runtime = None
    if case == 'runtime_recurrence':
        require(len(expected_hashes) == 1, 'runtime loop bounds changed compiled binary')
        visits = {}
        for row in records:
            actor = json.dumps(row['actor'], sort_keys=True)
            key = (row['site'], row['invocation_id'], row['program'], actor)
            visits.setdefault(key, set()).add(row['occurrence'])
        per_site = {}
        for (site, invocation, _, _), occurrences in visits.items():
            per_site.setdefault(site, {}).setdefault(invocation, set()).add(len(occurrences))
        matching = [site for site, calls in per_site.items() if len(calls) == 2
                    and any(sorted([a, b]) in ([2, 5], [3, 6])
                            for a in list(calls.values())[0] for b in list(calls.values())[1])]
        require(matching, 'same-binary loop does not expose exact2/5 body or3/6 header visits')
        runtime = {'same_binary': True, 'sites_with_exact_runtime_multiplicity': matching}
    timing = load(bundle / 'ai' / 'export_timing.json')
    require(timing.get('schema_version') == 1 and timing.get('clock') == 'host.monotonic' and timing.get('unit') == 'seconds', 'export timing schema/units')
    require(timing.get('complete_finalize_and_export') is True, 'incomplete host finalize/export timing')
    phases = timing.get('phases', {})
    require(all(number(value) and value >= 0 for value in phases.values()), 'invalid export phase duration')
    require(all(key in phases for key in ['collector_finalize_s', 'bundle_materialization_s']), 'CLI timing omits finalize/materialization')
    wall = timing.get('export_wall_s')
    require(number(wall) and 0 <= wall <= 60 and math.isclose(wall, sum(phases.values()), rel_tol=1e-8, abs_tol=1e-6), 'export budget/phase sum failure')
    require(timing.get('scope') == 'collector_finalize_then_bundle_export', 'incorrect CLI export measured scope')
    deadlines = load(bundle / 'ai' / 'deadlines.json')
    require(deadlines.get('schema_version') == 1 and deadlines.get('enforced') is True, 'automatic CLI watchdog not enforced')
    require(integer(deadlines.get('supervisor_worker_launches')) and deadlines['supervisor_worker_launches'] == 1, 'CLI launched multiple application workers')
    limits = deadlines.get('limits_seconds', {})
    require(number(limits.get('startup')) and limits['startup'] > 0, 'invalid startup watchdog limit')
    require(number(limits.get('compile')) and 0 < limits['compile'] <= baseline['cold_timeout_s'], 'compile budget was silently loosened')
    require(number(limits.get('export')) and 0 < limits['export'] <= 60, 'export watchdog was silently loosened')
    require(deadlines.get('application_runtime_limit') is None, 'default CLI altered application runtime policy')
    require((bundle / 'ai' / 'execution.json').is_file(), 'missing actual compiler execution organization view')
    metrics.update({'status': 'pass', 'backend': backend, 'case': case, 'binary_ids': sorted(expected_hashes),
                    'invocation_ids': sorted(invocations), 'source_linked_device_records': len(records),
                    'additional_partial_records_retained': partial_records,
                    'plan_summary': plan_summary, 'loss': losses, 'runtime_loop': runtime,
                    'complete_finalize_export_s': wall, 'report': verify_report(bundle, records),
                    'limits': ['HTML links and source/identity data checked; interactive browser controls not executed here.',
                               'Raw capture accounting and immutable artifacts checked; product device-origin implementation remains independently reviewed.']})
    return metrics


def main():
    p = argparse.ArgumentParser()
    p.add_argument('bundle', type=Path)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--cohort', type=Path, required=True)
    p.add_argument('--backend', choices=['nvidia', 'enflame', 'ascend'], required=True)
    p.add_argument('--case', required=True)
    p.add_argument('--shape-index', type=int, required=True)
    p.add_argument('--config-index', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    require(not args.output.exists(), 'refuse to overwrite an earlier qualification result')
    require(not args.output.resolve().is_relative_to(args.bundle.resolve()), 'checker result must remain outside immutable bundle')
    try:
        result = verify(args.bundle, args.receipt, args.cohort, args.backend, args.case, args.shape_index, args.config_index)
    except (ContractError, KeyError, TypeError, ValueError, OSError, StopIteration) as error:
        result = {'status': 'fail', 'error_type': type(error).__name__, 'error': str(error)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    raise SystemExit(0 if result['status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
