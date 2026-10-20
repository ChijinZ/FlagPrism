"""Source-selection and cache tests, executed in the existing Ascend Docker."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parser = argparse.ArgumentParser()
parser.add_argument('--plan', type=Path, required=True)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--baseline-plan', type=Path, required=True)
parser.add_argument('--capture', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
plan = load('candidate_plan', args.plan)
baseline = load('baseline_plan', args.baseline_plan)

region = dict(controlId=10, regionIndex=0, blockIndex=0, repeated=True)


def row(identity, operation, *, body=False):
    return dict(opId=identity,
                mlirOpName=operation,
                sourceLoc=f'loc("selection.py":{identity}:1)',
                result=dict(valueKind='tensor' if body else 'scalar',
                            elementDtype='f32'),
                isKernelEntryContext=not body,
                controlFlowAncestors=[region] if body else [])


table = [
    row(1, 'tt.get_program_id'),
    row(2, 'arith.addi'),
    row(3, 'tt.load', body=True),
    row(4, 'tt.load', body=True),
    row(5, 'tt.reduce', body=True),
    row(6, 'tt.dot', body=True),
    row(7, 'tt.store')
]
for budget in (1, 2, 3, 8):
    result = plan.plan_operations(table, budget, census=True, timeline=True)
    need(
        result['selected_sites'][0] == 6
        and len(result['selected_sites']) <= budget,
        'Timeline did not reserve the actual contraction within budget')
    need(
        plan.plan_operations(table, budget,
                             census=True) == baseline.plan_operations(
                                 table, budget, census=True),
        'Counter selection changed')
reordered = list(reversed(table))
need(
    plan.plan_operations(reordered, 1, census=True,
                         timeline=True)['selected_sites'] == [6],
    'Input ordering hid the contraction')
condition = [
    dict(r, isControlConditionComputation=True) if r['opId'] == 6 else r
    for r in table
]
need(
    plan.plan_operations(condition, 1, census=True,
                         timeline=True)['selected_sites'] == [5],
    'Condition computation became a body aggregate')

capture = json.loads(args.capture.read_text())
tracked = capture['metadata']['compiler_metadata']['debug_tracked_table']
actual = plan.plan_operations(tracked, 8, census=True, timeline=True)
old = baseline.plan_operations(tracked, 8, census=True)
by_id = {r['opId']: r for r in tracked}
dot_ids = {key for key, r in by_id.items() if r['mlirOpName'] == 'tt.dot'}
need(bool(dot_ids.intersection(actual['selected_sites'])),
     'The retained matrix case still omits its contraction')
need(not dot_ids.intersection(old['selected_sites']),
     'Retained case no longer reproduces the old omission')
need(
    plan.plan_operations(tracked, 8, census=True) == old,
    'Actual counter plan changed')

# Use the installed native/compiler dependencies, but the new Python modules.
# This is a source-level cache check; the subsequent normal installation and
# public matrix run establish the actual pre-lookup behavior.
import torch  # noqa: E402,F401 -- initialize Torch before its Triton integration
import torch_npu  # noqa: E402,F401 -- same import order as normal NPU applications

sys.modules['flagtree.debugger.automatic_plan'] = plan
compiler = load('flagtree.debugger._selection_candidate', args.compiler)
request = dict(automatic=True,
               semantics=['source_control_interval'],
               program_policy='runtime_first_last')
first = compiler._gcu_publication_config(
    dict(debug_observation_request=request))
version = plan.TIMELINE_SELECTION_POLICY_VERSION
try:
    plan.TIMELINE_SELECTION_POLICY_VERSION = version + 1
    changed = compiler._gcu_publication_config(
        dict(debug_observation_request=request))
finally:
    plan.TIMELINE_SELECTION_POLICY_VERSION = version
need(
    first['debug_timeline_selection_policy_version'] == version
    and changed['debug_timeline_selection_policy_version'] == version + 1
    and first != changed,
    'Timeline policy is absent from compile configuration')
counter = compiler._gcu_publication_config(
    dict(debug_observation_request=dict(automatic=True,
                                        semantics=['counter'],
                                        program_policy='all_grid_census')))
need('debug_timeline_selection_policy_version' not in counter,
     'Timeline policy changed counter cache configuration')

(args.output / 'result.json').write_text(
    json.dumps(dict(status='timeline_selection_source_checks_passed',
                    actual_old_selected=old['selected_sites'],
                    actual_new_selected=actual['selected_sites'],
                    actual_selected_operations=[
                        by_id[key]['mlirOpName']
                        for key in actual['selected_sites']
                    ],
                    timeline_policy_version=version,
                    counter_plan_unchanged=True,
                    public_install_verified=False,
                    device_executed=False),
               indent=2))
