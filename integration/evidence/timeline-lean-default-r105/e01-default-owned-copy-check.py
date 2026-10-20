"""CPU-only current default decode of an owned original E01 copy."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from unittest import mock
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
os.environ.update(TORCH_DEVICE_BACKEND_AUTOLOAD='0',FLAGTREE_BACKEND='ascend',USE_FLAGCX='OFF',USE_FLIR='OFF',USE_FLAGPRISM='OFF')
original=Path('/tmp/chijin-timeline-r077-ascend/runs/recover-v1/output/device');target=a.output/'device';shutil.copytree(original,target)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
original_files={str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()};before=sum(p.stat().st_size for p in (target/'capture').rglob('*') if p.is_file())
from flagtree.profiler.timeline_capture_store import load_capture
from flagtree.profiler.timeline_ascend import AscendTimelineCollector
from flagtree.profiler import timeline_ascend_machine,timeline_ascend_fragment_store
from flagtree.debugger import api
root=target/'capture/timeline';index=json.loads((root/'index.json').read_text());captures=[load_capture(root,row['capture_file']) for row in index['captures']]
if len(captures)!=10:raise ValueError('Not original ten-call cohort')
collector=object.__new__(AscendTimelineCollector);collector._timeline_pending={c['owner']['invocation_id']:r['capture_file'] for r,c in zip(index['captures'],captures)};collector._timeline_rows=[]
existing={c['owner']['binary_id']:c['machine_counter_mapping'] for c in captures};before_exports=len(api._exported_runs)
def cached_machine(directory,*,metadata,deadline):return existing[metadata['compiler_metadata']['hash']]
def forbidden(*args,**kwargs):raise RuntimeError('CPU default regression attempted external tool/optional static analysis')
try:
 with mock.patch.object(timeline_ascend_machine,'inspect_capture_binary',cached_machine),mock.patch.object(timeline_ascend_fragment_store,'inspect_capture_fragments',forbidden),mock.patch.object(subprocess,'Popen',forbidden):
  for capture in captures:collector._decode_timeline_original(capture['owner']['invocation_id'],root,time.monotonic()+60)
finally:del api._exported_runs[before_exports:]
after=sum(p.stat().st_size for p in (target/'capture').rglob('*') if p.is_file());newcaptures=[load_capture(root,row['capture_file']) for row in index['captures']]
if collector._timeline_pending or len(collector._timeline_rows)!=10:raise ValueError('Not all original calls finalized')
if after>67108864 or (root/'analysis/ascend-fragments').exists() or any('source_fragment_paths' in c for c in newcaptures):raise ValueError('Current default added heavy analysis or exceeded original budget')
for name,h in original_files.items():
 if sha(original/name)!=h:raise ValueError('Original evidence changed')
 if name.endswith(('.bin','.pftrace')) and sha(target/name)!=h:raise ValueError('Actual raw or Perfetto changed')
for old,new in zip(captures,newcaptures):
 if old['raw_sha256']!=new['raw_sha256'] or not new.get('counter_ns_exports'):raise ValueError('Core raw/time export lost')
 if old.get('observed_dependency_exports') and not new.get('observed_dependency_exports'):raise ValueError('Existing dependency export lost')
(a.output/'result.json').write_text(json.dumps(dict(status='current_default_reprocesses_original_E01_without_auxiliary_graphs',calls=10,binaries=len(existing),source_commit='6e78f136214da74254211fa19b90a3f7b7353fa2',complete_bundle_before=before,complete_bundle_after=after,budget_bytes=67108864,originals_unchanged=True,original_raw_and_standard_perfetto_unchanged=True,counter_time_exports_preserved=True,existing_dependency_exports_preserved=True,automatic_fragment_analysis_called=False,external_tools_executed=False,machine_mapping_basis='same immutable original E01 cached machine facts; native path unchanged',application_replayed=False,device_executed=False),indent=2))
