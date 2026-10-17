"""CPU mechanism fixtures, not actual device/clock/flow qualification."""
import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--module', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('async_rules', a.module)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    plan = {'timeline_plan_version': 1, 'timeline_record_version': 2,
            'schema_version': 2, 'binary_id': 'bin', 'timeline_async_boundary_count': 5,
            'inventory': [
                {'selected': True, 'scope_id': 0, 'timeline_mechanism': 'nvidia.cp_async.submit'},
                {'selected': True, 'scope_id': 1, 'timeline_mechanism': 'nvidia.cp_async.commit'},
                *[{'selected': True, 'scope_id': 2 + n,
                   'timeline_mechanism': 'nvidia.cp_async.wait',
                   'timeline_wait_pending': n} for n in range(3)]]}
    identity = dict(capture_id='capture', invocation_id='invocation', binary_id='bin')
    passed = []

    def fixture(sequence, observers=1):
        records, rows = [], []
        for warp in range(observers):
            for index, site in enumerate(sequence):
                for phase in range(2):
                    seq = index * 2 + phase
                    records.append({'program': 0, 'warp': warp, 'site': site,
                                    'sequence': seq, 'tick': (1 << 60) + seq * 100,
                                    'phase': 'exit' if phase else 'entry',
                                    'raw_byte_offset': 32 + warp * 131072 + seq * 16,
                                    'raw_byte_length': 16})
            rows.append({'program': 0, 'warp': warp, 'complete': True,
                         'written_records': len(sequence) * 2,
                         'retained_records': len(sequence) * 2,
                         'overwritten_records': 0, 'saturated': False})
        return {'record_version': 2, 'complete': True, 'records': records, 'observers': rows}

    def derive(decoded, selected_plan=None, **ids):
        return mod.derive_cp_async_facts(decoded, plan if selected_plan is None else selected_plan,
                                         **dict(identity, **ids))

    def check(name, condition):
        if not condition:
            raise RuntimeError(name)
        passed.append(name)

    def rejects(name, decoded, selected_plan=None, **ids):
        try:
            derive(decoded, selected_plan, **ids)
        except ValueError:
            passed.append(name)
        else:
            raise RuntimeError('Accepted bad mechanism fixture: ' + name)

    result = derive(fixture([0, 0, 1, 2]))
    check('multi-submit-one-commit', len(result['groups']) == 1 and
          len(result['groups'][0]['submit_operation_ids']) == 2 and
          len(result['dependencies']) == 1)
    check('all-endpoint-and-member-proofs', len(result['dependencies'][0]['record_ids']) == 8 and
          all(r in result['records'] for r in result['dependencies'][0]['record_ids']))
    check('no-clock-or-engine-promotion', result['time_arrow_verified'] is False and
          result['dependencies'][0]['time_arrow_verified'] is False)
    partial = derive(fixture([0, 1, 0, 1, 0, 1, 3]))
    check('partial-wait-excludes-newest', partial['waits'][0]['direct_coverage_commit_range'] == [0, 2] and
          len(partial['dependencies']) == 2 and
          len(partial['observers'][0]['groups_not_covered_by_observed_wait']) == 1)
    drain = derive(fixture([0, 1, 0, 1, 0, 1, 3, 2]))
    check('drain-completes-only-remaining-group', len(drain['dependencies']) == 3 and
          len(drain['waits'][-1]['newly_guaranteed_group_ids']) == 1 and
          not drain['observers'][0]['groups_not_covered_by_observed_wait'])
    empty = derive(fixture([1, 2]))
    check('empty-commit-is-explicit', empty['groups'][0]['empty_recorded_submit_set'] and
          not empty['groups'][0]['submit_operation_ids'])
    repeat = derive(fixture([0, 1, 2, 0, 1, 2]))
    check('generations-not-iterations', [v['logical_commit_ordinal'] for v in repeat['groups']] == [0, 1] and
          all(v['iteration_id'] is None and v['buffer_slot'] is None for v in repeat['operations']))
    two = derive(fixture([0, 1, 2], observers=2))
    check('observer-state-isolation', len({v['id'] for v in two['groups']}) == 2 and
          all(len(v['newly_guaranteed_group_ids']) == 1 for v in two['waits']))
    check('capture-and-invocation-isolation', derive(fixture([0, 1, 2]), capture_id='other')['groups'][0]['id'] !=
          derive(fixture([0, 1, 2]), invocation_id='other')['groups'][0]['id'])
    repeated_wait = derive(fixture([0, 1, 2, 2]))
    check('repeated-consumer-guarantee-no-quadratic-edges', len(repeated_wait['dependencies']) == 1 and
          repeated_wait['waits'][1]['direct_coverage_commit_range'] == [0, 1] and
          not repeated_wait['waits'][1]['newly_guaranteed_group_ids'])
    long = derive(fixture([0, 1, 2] * 1000))
    check('linear-fact-count', len(long['dependencies']) == 1000 and
          long['waits'][-1]['known_guaranteed_commit_range'] == [0, 1000])
    lost = fixture([0, 1, 0, 1, 2])
    lost['complete'] = lost['observers'][0]['complete'] = False
    lost['observers'][0]['written_records'] += 2
    lost['observers'][0]['overwritten_records'] = 2
    check('loss-never-shifts-generations', not derive(lost)['groups'] and
          not derive(lost)['dependencies'] and not derive(lost)['record_stream_complete'])
    base = fixture([0, 1, 2])
    gap = copy.deepcopy(base)
    gap['records'][2]['sequence'] += 1
    rejects('missing-commit-record', gap)
    nested = copy.deepcopy(base)
    nested['records'][1]['site'], nested['records'][1]['phase'] = 1, 'entry'
    rejects('impossible-mechanism-nesting', nested)
    wrong_plan = copy.deepcopy(plan)
    wrong_plan['binary_id'] = 'other'
    rejects('binary-manifest-mismatch', base, wrong_plan)
    for name, field, value in [('unknown-plan', 'timeline_plan_version', 9),
                               ('boolean-plan', 'timeline_plan_version', True),
                               ('float-record-version', 'timeline_record_version', 2.0),
                               ('wrong-count', 'timeline_async_boundary_count', 4)]:
        bad = copy.deepcopy(plan)
        bad[field] = value
        rejects(name, base, bad)
    for name, field, value in [('excluded-commit', 'selected', False),
                               ('unknown-mechanism', 'timeline_mechanism', 'fake')]:
        bad = copy.deepcopy(plan)
        bad['inventory'][1][field] = value
        rejects(name, base, bad)
    for name, value in [('boolean-wait', True), ('excess-wait', 8)]:
        bad = copy.deepcopy(plan)
        bad['inventory'][2]['timeline_wait_pending'] = value
        rejects(name, base, bad)
    bad = copy.deepcopy(base)
    bad['records'][2]['raw_byte_offset'] = bad['records'][0]['raw_byte_offset']
    rejects('aliased-raw-evidence', bad)
    bad = copy.deepcopy(base)
    bad['records'][2]['tick'] = bad['records'][1]['tick'] - 1
    rejects('cross-operation-clock-regression', bad)
    bad = copy.deepcopy(base)
    bad['observers'][0]['complete'] = False
    rejects('capture-observer-completeness-mismatch', bad)
    rejects('empty-capture-identity', base, capture_id='')
    bad = copy.deepcopy(plan)
    bad['inventory'][1]['timeline_mechanism'] = []
    rejects('unhashable-mechanism-type', base, bad)
    bad = copy.deepcopy(base)
    bad['observers'][0] = []
    rejects('malformed-observer-type', bad)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({'status': 'cpu_contract_passed_not_device_qualification',
                                  'count': len(passed), 'passed': passed,
                                  'optimized_python': bool(sys.flags.optimize),
                                  'module_sha256': hashlib.sha256(a.module.read_bytes()).hexdigest(),
                                  'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + '\n')


if __name__ == '__main__':
    main()
