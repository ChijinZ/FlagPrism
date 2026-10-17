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
        for capture in captures:
            decoded = json.loads((output/'timeline'/capture['decoded_file']).read_text())
            records.extend(decoded['records'])
            facts = json.loads((output/'timeline'/capture['async_file']).read_text())
            require(not facts['time_arrow_verified'], 'Unverified facts became time arrows')
            groups += len(facts['groups'])
        require(groups > 0, 'Ordinary async GEMM lost dynamic logical group facts')
        require(len({c['owner']['binary_id'] for c in captures}) == 2, 'Mixed kernels not isolated')
        require(len({c['owner']['stream'] for c in captures[:3]}) == 2, 'Stream association lost')
        require((output/'manifest.json').is_file(), 'Standard bundle manifest missing')
        phases.append(dict(name=name, captures=len(captures), records=len(records),
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
    (args.output/'result.json').write_text(json.dumps(dict(
        status='public_collection_raw_stage_passed_not_full_P01', phases=phases,
        cli_argv=command, limitations=['Raw stage only; no physical clock/epoch proof',
            'No final marker-order or Perfetto/independent qualification']), indent=2)+'\n')


if __name__ == '__main__':
    main()
