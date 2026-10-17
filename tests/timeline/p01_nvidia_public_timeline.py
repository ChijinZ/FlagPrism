"""Actual public API/CLI collection; raw stage, not full clock/Perfetto P01."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    import torch
    import flagtree.profiler as profiler
    from flagtree.profiler.hooks.instrumentation import InstrumentationHook
    from flagtree.profiler.timeline_events import validate_raw_batch
    torch.cuda.set_device(0)
    require(torch.cuda.get_device_capability() == (12, 0), 'Wrong booked device')
    target = Path(__file__).with_name('ordinary_timeline_workload.py')
    spec = importlib.util.spec_from_file_location('ordinary_timeline_workload', target)
    workload = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = workload
    spec.loader.exec_module(workload)
    phases = []

    def verify(name):
        output = args.output/name
        index = json.loads((output/'timeline/index.json').read_text())
        require(index['status'] == 'partial_clock_unverified', 'Unproven clock was upgraded')
        require(len(index['captures']) == 4, 'Not exactly requested four kernels')
        captures = [json.loads((output/'timeline'/row['capture_file']).read_text())
                    for row in index['captures']]
        require(all(c['capture_status']=='raw_complete' for c in captures), 'Public capture incomplete')
        records = []
        groups = 0
        canonical_intervals = 0
        for capture in captures:
            decoded = json.loads((output/'timeline'/capture['decoded_file']).read_text())
            records.extend(decoded['records'])
            facts = json.loads((output/'timeline'/capture['async_file']).read_text())
            canonical = validate_raw_batch(json.loads(
                (output/'timeline'/capture['events_file']).read_text()))
            require(canonical['complete'] and len(canonical['records'])==len(decoded['records']),
                    'Canonical events lost raw records')
            require(all(e['kind']=='interval' for e in canonical['events']),
                    'Ordinary complete capture has incomplete intervals')
            canonical_intervals += len(canonical['events'])
            mapping = canonical['backend_record_map']['nvidia.cp_async.groups.v1']
            require(all(r in mapping for r in facts['records']),
                    'Mechanism facts are not linked to canonical records')
            require(not facts['time_arrow_verified'], 'Unverified facts became time arrows')
            groups += len(facts['groups'])
        require(groups > 0, 'Ordinary async GEMM lost dynamic logical group facts')
        require(len({c['owner']['binary_id'] for c in captures}) == 2, 'Mixed kernels not isolated')
        require(len({c['owner']['stream'] for c in captures[:3]}) == 2, 'Stream association lost')
        require((output/'manifest.json').is_file(), 'Standard bundle manifest missing')
        phases.append(dict(name=name, captures=len(captures), records=len(records),
                           canonical_intervals=canonical_intervals,
                           logical_groups=groups,
                           binaries=[c['owner']['binary_id'] for c in captures],
                           invocations=[c['owner']['invocation_id'] for c in captures]))

    # Same JIT objects across API sessions exercise cached loaded handles.
    for name in ('api-cold', 'api-warm'):
        session = profiler.start(str(args.output/name), detail='timeline')
        try:
            workload.run(args.output/(name+'-math'))
        finally:
            profiler.finalize(session)
        verify(name)
        require(not InstrumentationHook.active_count, 'Hook did not deactivate')
    require(phases[0]['binaries'] == phases[1]['binaries'], 'Warm session changed compiled identity')
    # A failed export must still close the native collector and retain owners
    # for raw-only recovery, without executing the ordinary workload again.
    profile_module = importlib.import_module('flagtree.profiler.profile')
    session = profiler.start(str(args.output/'api-export-failure'), detail='timeline')
    hook = profile_module._active_sessions[session]['timeline_hook']
    original_flush = hook.flush_timeline
    workload.run(args.output/'api-export-failure-math')
    def fail_export(base):
        raise OSError('injected public timeline export failure')
    hook.flush_timeline = fail_export
    try:
        profiler.finalize(session)
    except RuntimeError as error:
        require('injected public timeline export failure' in str(error), 'Wrong export failure')
        (args.output/'export-failure.txt').write_text(str(error)+'\n')
    else:
        raise RuntimeError('Injected export failure was ignored')
    require(session not in profile_module._active_sessions and not InstrumentationHook.active_count,
            'Failed finalization left session/hooks active')
    recovered = original_flush(str(args.output/'recovered-raw'))
    recovery_index = json.loads((recovered/'index.json').read_text())
    require(len(recovery_index['captures']) == 4 and not hook.timeline_pool.invocation_ids,
            'Raw recovery replayed/lost calls or leaked owners')
    phases.append(dict(name='api-export-failure-recovered', captures=4,
                       raw_directory=str(recovered)))
    session = profiler.start(str(args.output/'api-after-failure'), detail='timeline')
    try:
        workload.run(args.output/'api-after-failure-math')
    finally:
        profiler.finalize(session)
    verify('api-after-failure')
    session = profiler.start(str(args.output/'api-overflow'), detail='timeline')
    try:
        workload.run_overflow(args.output/'api-overflow-math')
    finally:
        profiler.finalize(session)
    overflow_prefix = args.output/'api-overflow/timeline'
    overflow_index = json.loads((overflow_prefix/'index.json').read_text())
    require(len(overflow_index['captures'])==1, 'Overflow replayed the application')
    overflow = json.loads((overflow_prefix/overflow_index['captures'][0]['capture_file']).read_text())
    canonical = validate_raw_batch(json.loads((overflow_prefix/overflow['events_file']).read_text()))
    require(overflow['capture_status']=='incomplete' and not canonical['complete'],
            'Lost history became a complete capture')
    require(any(o['overwritten_records']>0 for o in canonical['observers']), 'Overflow was not actually triggered')
    require(any(e['kind']=='incomplete' for e in canonical['events']), 'Lost endpoints were hidden or synthesized')
    overflow_facts = json.loads((overflow_prefix/overflow['async_file']).read_text())
    require(not overflow_facts['groups'] and not overflow_facts['dependencies'],
            'Loss produced inferred group generations')
    phases.append(dict(name='api-overflow', captures=1,
        canonical_intervals=sum(e['kind']=='interval' for e in canonical['events']),
        incomplete_intervals=sum(e['kind']=='incomplete' for e in canonical['events'])))
    command = [sys.executable, '-I', '-m', 'flagtree.profiler.cli', '--detail', 'timeline',
               '--device', '0', '-n', str(args.output/'cli'), str(target),
               '--evidence', str(args.output/'cli-math')]
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    # The outer development owner bounds this subprocess and its descendants;
    # the actual CLI also exercises its own compile/export supervisor.
    with (args.output/'cli.stdout.log').open('wb') as out, (args.output/'cli.stderr.log').open('wb') as err:
        code = subprocess.run(command, stdout=out, stderr=err, env=env).returncode
    require(code == 0, 'Public CLI failed: '+(args.output/'cli.stderr.log').read_text())
    verify('cli')
    legacy_command = [sys.executable, '-I', '-m', 'flagtree.profiler.cli', '--detail', 'auto',
        '--device', '0', '-n', str(args.output/'legacy-auto'), str(target),
        '--evidence', str(args.output/'legacy-auto-math'), '--skip-zero']
    with (args.output/'legacy.stdout.log').open('wb') as out, (args.output/'legacy.stderr.log').open('wb') as err:
        code = subprocess.run(legacy_command, stdout=out, stderr=err, env=env).returncode
    require(code == 0, 'Legacy automatic count path failed: '+(args.output/'legacy.stderr.log').read_text())
    legacy = json.loads((args.output/'legacy-auto/ai/observations.json').read_text())
    require(len(legacy.get('captures', [])) == 4 and legacy.get('observations'),
            'Legacy count observations disappeared')
    require(not (args.output/'legacy-auto/timeline').exists(), 'Count mode became timeline mode')
    (args.output/'result.json').write_text(json.dumps(dict(
        status='public_collection_raw_stage_passed_not_full_P01', phases=phases,
        cli_argv=command, legacy_argv=legacy_command,
        legacy_count_captures=len(legacy['captures']),
        limitations=['Raw stage only; no physical clock/epoch proof',
            'No final marker-order or Perfetto/independent qualification']), indent=2)+'\n')


if __name__ == '__main__':
    main()
