"""Q4 adapter: unchanged public checker plus the original exact runtime-visit rule.

The Q4 seed/witness receipt layout differs from Q2; validate it explicitly rather
than changing the frozen common checker or mathematical source. Server Docker only.
"""
import argparse
import json
from pathlib import Path
import tempfile
import check_common_report as common


def exact_runtime_sites(records):
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
    common.require(matching, 'same-binary loop does not expose exact2/5 body or3/6 header visits')
    return matching


def verify(bundle, receipt_path, eligibility_path, backend):
    receipt, eligibility = common.load(receipt_path), common.load(eligibility_path)
    common.require(eligibility.get('profiler_invoked') is False, 'reserve eligibility was not ordinary baseline')
    original = next(row['receipt'] for row in eligibility['results']
                    if row['status'] == 'pass' and all(row[key] == receipt[key]
                    for key in ['case', 'shape_index', 'config_index']))
    common.require(receipt['output_initial_sha256'] == original['output_initial_sha256'], 'Q4 output dependency seed changed')
    common.require([c['runtime_steps'] for c in receipt['calls']] == [2, 5], 'Q4 runtime requests changed')
    for call, baseline in zip(receipt['calls'], original['calls']):
        common.require(call['non_idempotence_witness_max_abs'] == baseline['non_idempotence_witness_max_abs'], 'Q4 mathematical replay witness changed')
    # The shared checker expects a single top-level witness for Q2. Q4 keeps one
    # witness per call, checked above. Omit only that layout-specific seed branch
    # from its metadata adapter, having validated the actual seed independently.
    adapted = {key: original[key] for key in ['case', 'shape_index', 'config_index', 'shape', 'config', 'grid', 'input_sha256', 'calls']}
    adapted['cold_timeout_s'] = 120
    cohort = {'source_sha256': eligibility['source_sha256'],
              'cases': [{'case': receipt['case'], 'source': 'reserve_dynamic.py'}],
              'backend_evidence': {backend: {'common_combinations': [adapted], 'runtime_probe': []}}}
    with tempfile.TemporaryDirectory(prefix='qualification-q4-metadata-') as tmp:
        path = Path(tmp) / 'cohort.json'
        path.write_text(json.dumps(cohort))
        metrics = common.verify(bundle, receipt_path, path, backend, receipt['case'], receipt['shape_index'], receipt['config_index'])
    hashes = {call['compiled_kernel_hash'] for call in receipt['calls']}
    common.require(len(hashes) == 1, 'Q4 runtime bounds changed compiled binary')
    fine = common.load(bundle / 'ai/fine_grained.json')
    binaries = {row['id']: row for row in common.load(bundle / 'ai/binaries.json')}
    binary_id = next(iter(hashes))
    source = binaries[binary_id]['source']
    lines = common.inside(bundle, source['file_snapshot_file']).read_text().splitlines()
    start = next(i for i, line in enumerate(lines, 1) if line.startswith(f"def {receipt['case']}("))
    end = next((i for i in range(start + 1, len(lines) + 1) if lines[i - 1].startswith('def ')), len(lines) + 1)
    records = [row for row in fine['records'] if row['binary_id'] == binary_id
               and row['semantic'] != 'native_lifecycle' and row['association_status'] == 'verified'
               and row['source_status'] == 'located' and all(row[key] is not None for key in ['program', 'actor', 'site', 'occurrence', 'operation'])
               and any(loc['file'] == source['path'] and common.integer(loc['line']) and start <= loc['line'] < end
                       for loc in row['source_locations'])]
    metrics['runtime_loop'] = {'same_binary': True, 'sites_with_exact_runtime_multiplicity': exact_runtime_sites(records)}
    metrics['reserve_revision'] = 'Q4'
    metrics['ordinary_baseline_eligibility_sha256'] = common.digest(eligibility_path)
    return metrics


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--eligibility', type=Path, required=True)
    p.add_argument('--backend', choices=['nvidia', 'enflame', 'ascend'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    common.require(not a.output.exists() and not a.output.resolve().is_relative_to(a.bundle.resolve()), 'refuse overwrite or mutation of bundle')
    try:
        result = verify(a.bundle, a.receipt, a.eligibility, a.backend)
    except (common.ContractError, KeyError, TypeError, ValueError, OSError, StopIteration) as error:
        result = {'status': 'fail', 'error_type': type(error).__name__, 'error': str(error)}
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    raise SystemExit(0 if result['status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
