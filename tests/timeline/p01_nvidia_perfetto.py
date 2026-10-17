"""Actual public NVIDIA capture and isolated counter-ns Perfetto, not full P01."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    result = importlib.util.module_from_spec(spec);sys.modules[name]=result
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args();args.output.mkdir(exist_ok=False)
    import torch
    import flagtree.profiler as profiler
    from flagtree.profiler.timeline_events import validate_raw_batch
    from flagtree.profiler.timeline_views import CounterUnitProof, derive_counter_ns_views, document_sha256
    from flagtree.profiler.timeline_perfetto import write_counter_exports, validate_counter_view
    torch.cuda.set_device(0)
    need(torch.cuda.get_device_capability()==(12,0), 'Wrong functional target')
    workload = module('ordinary_timeline_workload')
    bundle = args.output/'capture'
    session = profiler.start(str(bundle), detail='timeline')
    try:
        workload.run(args.output/'math')
    finally:
        profiler.finalize(session)
    root = bundle/'timeline'
    index = json.loads((root/'index.json').read_text())
    need(len(index['captures'])==4 and not index['retained_owners'] and not index['pending_decode'],
         'Actual default captures/ownership incomplete')
    manifest = []
    endpoints = 0
    for item in index['captures']:
        capture = json.loads((root/item['capture_file']).read_text())
        need(capture['counter_ns_status']['status']=='counter_unit_only',
             'Actual counter unit export unavailable: '+str(capture.get('counter_ns_status')))
        batch = validate_raw_batch(json.loads((root/capture['events_file']).read_text()))
        before = document_sha256(batch)
        raw = (root/capture['raw_file']).read_bytes()
        need(hashlib.sha256(raw).hexdigest()==batch['raw_artifact']['sha256'], 'Raw association mismatch')
        endpoints += len(batch['records'])
        need(capture['counter_ns_exports'], 'No actual standard trace produced')
        for export in capture['counter_ns_exports']:
            view_file = root/export['view_file'];trace_file = root/export['trace_file']
            view = json.loads(view_file.read_text())
            validate_counter_view(view, batch)
            need(view['unit_proof']['provider']=='nvidia.sm120.globaltimer_counter_unit.v1', 'Not actual getter unit provider')
            need(view['read_precision_status']=='unverified' and not view['time_arrows_verified'],
                 'Unit evidence became timing/flow qualification')
            manifest.append(dict(view_file=str(view_file),trace_file=str(trace_file),sha256=export['sha256'],fixture=False))
        need(document_sha256(batch)==before, 'Export changed canonical observations')
    need((root/'index.html').is_file(), 'No standard trace opening index')
    # A separate, prominently labelled nested atomic-pair fixture tests the
    # append-order projection. It does not count as real GCU device coverage.
    fixture = module('test_enflame_timeline_events').convert()
    proof = CounterUnitProof(**fixture['identity'], raw_sha256=fixture['raw_artifact']['sha256'],
        observer_id=fixture['observers'][0]['id'], period_numerator_ns=1,
        period_denominator=1, max_elapsed_ns=1000, provider='test.fixture_only',
        evidence_ids=('synthetic_nested_pairs_not_device_evidence',))
    views = derive_counter_ns_views(fixture,[proof])
    fixture_rows = write_counter_exports(args.output, Path('fixture'), views, fixture)
    for export in fixture_rows:
        manifest.append(dict(view_file=str(args.output/export['view_file']),
            trace_file=str(args.output/export['trace_file']),sha256=export['sha256'],fixture=True))
    path = args.output/'trace-manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
    tool_python = '/workspace/chijin-timeline-r003/runs/perfetto-tools-offline-v1/output/venv/bin/python'
    command = [tool_python,'-I',str(Path(__file__).with_name('verify_perfetto_traces.py')),
               '--manifest',str(path),'--output',str(args.output/'TP')]
    with (args.output/'TP.stdout.log').open('xb') as out,(args.output/'TP.stderr.log').open('xb') as err:
        code = subprocess.run(command, stdout=out, stderr=err).returncode
    need(code==0, 'Actual protobuf/TP verifier failed; inspect TP.stderr.log')
    result = json.loads((args.output/'TP/result.json').read_text())
    (args.output/'result.json').write_text(json.dumps(dict(
        status='real_nvidia_counter_ns_Perfetto_TP_passed_not_full_P01', math_calls=4,
        real_traces=sum(not row['fixture'] for row in manifest),
        fixture_traces=sum(row['fixture'] for row in manifest), raw_endpoints=endpoints,
        real_TP_slices=sum(row['slices'] for row in result['checks'] if not row['fixture']),
        clock_precision_qualified=False, source_boundaries_qualified=False,
        async_qualified=False, UI_qualified=False),indent=2)+'\n')


if __name__ == '__main__':
    main()
