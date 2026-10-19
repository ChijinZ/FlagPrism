"""Real retained-device captures re-exported in fresh guarded processes.

This is an offline retention/export check, not hardware clock qualification.
The original mathematical workload is never imported or executed here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument(
        '--original-timeline',
        type=Path,
        default=Path(
            '/workspace/chijin-timeline-r017/runs/counter-perfetto-v2/output/capture/timeline'
        ))
    parser.add_argument('--expected-captures', type=int, default=4)
    parser.add_argument('--expected-traces', type=int, default=32)
    parser.add_argument('--forbidden-root', action='append')
    parser.add_argument(
        '--require-original-trace-bytes',
        action='store_true',
        help=
        'For storage-only deltas, require exact bytes from the prior UI-checked capture'
    )
    parser.add_argument(
        '--defer-trace-processor',
        action='store_true',
        help=
        'Only test fresh-process offline reconstruction; validate the emitted manifest with the independent TP tools separately'
    )
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    forbidden = [
        str(Path(p).resolve()).rstrip('/') + '/'
        for p in (args.forbidden_root or ['/workspace/chijin-timeline-r017/'])
    ]
    need(
        any(args.original_timeline.resolve().is_relative_to(Path(p))
            for p in forbidden),
        'The denied environment roots must include the original timeline/cache'
    )
    root = args.output / 'retained-timeline'
    need(
        not any(root.resolve().is_relative_to(Path(p)) for p in forbidden),
        'The copied offline bundle must be outside all denied environment roots'
    )
    shutil.copytree(args.original_timeline, root)
    cwd = args.output / 'empty-working-directory'
    cwd.mkdir()
    originals = {
        str(p.relative_to(root)): digest(p)
        for p in root.rglob('*') if p.is_file()
    }
    env = dict(os.environ,
               CUDA_VISIBLE_DEVICES='',
               TORCH_DEVICE_BACKEND_AUTOLOAD='0',
               TRITON_CACHE_DIR=str(args.output / 'empty-cache'))
    env.pop('PYTHONPATH', None)
    steps = []

    def run(name, command, environment=env):
        with (args.output / (name + '.stdout.log')).open('xb') as out, (
                args.output / (name + '.stderr.log')).open('xb') as err:
            proc = subprocess.Popen(command,
                                    stdout=out,
                                    stderr=err,
                                    env=environment,
                                    cwd=cwd)
            fields = Path(f'/proc/{proc.pid}/stat').read_text().rsplit(
                ')', 1)[1].split()
            row = dict(name=name,
                       pid=proc.pid,
                       startticks=int(fields[19]),
                       argv=command)
            steps.append(row)
            (args.output / 'steps.json').write_text(json.dumps(steps,
                                                               indent=2))
            row['returncode'] = proc.wait()
            (args.output / 'steps.json').write_text(json.dumps(steps,
                                                               indent=2))
            need(row['returncode'] == 0,
                 name + ' failed; inspect retained stderr')
        return json.loads(
            (args.output /
             (name + '.stdout.log')).read_text()) if name != 'TP' else None

    first = run('public-module', [
        sys.executable, '-I', '-m', 'flagtree.profiler.timeline_reexport',
        str(root)
    ])
    # Prevent dependence on the old live bundle/source/cache as well as hidden
    # subprocess-based application replay. CUDA hiding alone does not prove
    # that non-CUDA devices are unavailable; the denied paths are explicit.
    wrapper = '''import sys,runpy,json
def audit(event,args):
 if event=='subprocess.Popen':raise RuntimeError('Offline exporter attempted to start a child')
 if event=='open' and isinstance(args[0],str) and args[0].startswith(forbidden):
  raise RuntimeError('Offline exporter attempted to read the original environment: '+args[0])
 if event=='exec' and args[0].co_filename.startswith(forbidden):
  raise RuntimeError('Offline exporter attempted to execute the original workload')
forbidden=tuple(json.loads(sys.argv[2]))
sys.addaudithook(audit)
sys.argv=['flagtree.profiler.timeline_reexport',sys.argv[1]]
runpy.run_module('flagtree.profiler.timeline_reexport',run_name='__main__')
'''
    second = run('isolated-normal', [
        sys.executable, '-I', '-c', wrapper,
        str(root),
        json.dumps(forbidden)
    ])
    third = run('isolated-optimized', [
        sys.executable, '-I', '-O', '-c', wrapper,
        str(root),
        json.dumps(forbidden)
    ])
    need(first == second == third,
         'Same original inputs changed re-export identity')
    need(
        first['application_replayed'] is False
        and len(first['captures']) == args.expected_captures,
        'Unexpected captures or application execution report')
    for name, expected in originals.items():
        if name != 'index.html':
            need(
                digest(root / name) == expected,
                'Re-export modified original artifact: ' + name)
    manifest = []
    prior_traces = {}
    for file in args.original_timeline.glob('captures/*.json'):
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(file)
        for row in capture.get('counter_ns_exports', []):
            prior_traces[row['observer_id']] = row['sha256']
    for capture in first['captures']:
        need(
            capture['status'] == ('counter_unit_only'
                                  if args.expected_traces else 'raw_only'),
            'Unexpected unit-provider qualification')
        if not args.expected_traces:
            need(bool(capture['reason']),
                 'Raw-only export must explain missing unit evidence')
        canonical = json.loads((root / capture['canonical_file']).read_text())
        from flagtree.profiler.timeline_capture_store import load_capture_file
        original_capture = next(
            load_capture_file(root / row['capture_file'])
            for row in json.loads((root /
                                   'index.json').read_text())['captures']
            if row['invocation_id'] == capture['invocation_id'])
        original = json.loads(
            (root / original_capture['events_file']).read_text())
        need(original == canonical,
             'Offline decoder changed the original canonical semantics')
        for row in capture['exports']:
            if args.require_original_trace_bytes:
                need(
                    prior_traces.get(row['observer_id']) == row['sha256'],
                    'Storage-only delta changed UI-checked trace bytes')
            manifest.append(
                dict(view_file=str(root / row['view_file']),
                     trace_file=str(root / row['trace_file']),
                     sha256=row['sha256'],
                     fixture=False))
    need(
        len(manifest) == args.expected_traces,
        'Offline export lost actual observers or invented traces')
    path = args.output / 'trace-manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    # The independent reader has its own tools environment and may spawn TP.
    tool_python = '/workspace/chijin-timeline-r003/runs/perfetto-tools-offline-v1/output/venv/bin/python'
    if manifest and not args.defer_trace_processor:
        run('TP', [
            tool_python, '-I',
            str(Path(__file__).with_name('verify_perfetto_traces.py')),
            '--manifest',
            str(path), '--output',
            str(args.output / 'TP')
        ], dict(os.environ))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_retained_captures_offline_reexport_passed_not_full_P01',
            real_captures=args.expected_captures,
            real_traces=len(manifest),
            trace_processor_verified_here=bool(manifest)
            and not args.defer_trace_processor,
            trace_processor_deferred=bool(manifest)
            and args.defer_trace_processor,
            fresh_reexport_processes=3,
            original_artifacts_unchanged=len(originals) -
            int('index.html' in originals),
            original_environment_denied_in_two_processes=True,
            forbidden_environment_roots=forbidden,
            trace_bytes_match_prior_bundle=args.require_original_trace_bytes,
            application_replayed=False,
            raw_originals={
                name: sha
                for name, sha in originals.items() if name.endswith('.raw')
            },
            proof_limits=
            ('counter_unit_only; precision/boundary/async not qualified' if
             manifest else
             'raw_only; no validated unit, precision, source boundary or async qualification'
             )),
                   indent=2) + '\n')


if __name__ == '__main__':
    main()
