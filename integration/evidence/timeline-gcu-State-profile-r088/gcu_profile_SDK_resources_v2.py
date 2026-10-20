"""Read retained profile resource identities; inspect existing library symbols."""
import argparse,hashlib,json,subprocess,sys,re
from pathlib import Path
from flagtree.profiler._deadline import _stop_worker
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=Path('/tmp/chijin-timeline-r088-gcu/runs/source-partition-v1/output/actual-source/rows.json');rows=json.loads(reg.read_bytes());cohorts={};identities=[]
for row in rows:
 capfile=Path(row['capture_file']);need(sha(capfile)==row['capture_sha256'],'Original profile capture changed');cap=json.loads(capfile.read_bytes());meta=cap['metadata']['compiler_metadata'];identity=meta['debug_execution_tool_identity'];files=identity['files'];key=json.dumps(files,sort_keys=True)
 if key not in cohorts:
  folder=a.output/('cohort-'+str(len(cohorts)));folder.mkdir();copies=[]
  for path,digest in files.items():
   if path.endswith('/backends/enflame/compiler.py'):
    need(sha(path)==digest,'Actual registered backend compiler differs');p=Path(path);(folder/'compiler.py').write_bytes(p.read_bytes());copies.append(dict(path=path,sha256=digest,retained_file='compiler.py'))
    toolkit=p.with_name('toolkit.py');(folder/'toolkit.py').write_bytes(toolkit.read_bytes());copies.append(dict(path=str(toolkit),sha256=sha(toolkit),retained_file='toolkit.py'))
  cohorts[key]=dict(index=len(cohorts),copies=copies,registered_identity=identity)
 need(meta['arch']=='gcu300' and meta['backend_name']=='gcu' and meta['num_warps'] in (4,8),'Actual profile launch ABI differs');need(meta['debug_clock_library_sha256']==files['/opt/tops/llvm11/lib/krt/gcu300_api_profile.bc'],'Actual profile API library differs');identities.append(dict(stage=row['stage'],case=row['case'],capture_sha256=row['capture_sha256'],cohort=cohorts[key]['index'],arch=meta['arch'],num_warps=meta['num_warps'],profile_library_sha256=meta['debug_clock_library_sha256']))
library=Path('/opt/tops/llvm11/lib/krt/gcu300_api_profile.bc');need(sha(library)=='1a780215d7a63e34ce9c8cba6bfb126d222db726f5dca8802f3af0161fce81ec','Profile library changed');tool=Path('/opt/tops/llvm11/bin/opt');cmd=[str(tool),'-S',str(library),'-o',str(a.output/'profile-library.ll')]
with (a.output/'symbols.stdout').open('xb') as out,(a.output/'symbols.stderr').open('xb') as err:
 child=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
 try:child.wait(timeout=20)
 except BaseException:_stop_worker(child);raise
need(child.returncode==0,'Existing profile library symbol inspection failed')
symbols=(a.output/'profile-library.ll').read_text();wanted=['tops_memcpy_async','tops_deslice_async_1_si32','tops_deslice_async_2_si32','tops_slice_deslice_async_1_si32','tops_slice_deslice_async_2_si32','tops_slice_async_1_si32','tops_slice_async_2_si32','tops_slice_pad_async_1_si32','tops_slice_pad_async_2_si32','tops_get_thread_id','tops_get_block_id','tops_extsi_si32_to_si64','tops_minsi_si32','tops_maxsi_si32','tops_remsi_si32','tops_divsi_si32','tops_floordivsi_si32'];names=set(re.findall(r'^define[^\n]*?@([\w.$-]+)\(',symbols,re.M));overlaps=[n for n in wanted if n in names]
resources=[dict(path=str(p),sha256=sha(p)) for p in [library,tool,Path('/opt/triton_gcu/bin/gcu-compiler-compile'),Path('/opt/triton_gcu/lib/kurama/gcu300_tops_builtins.bc')]]
(a.output/'result.json').write_text(json.dumps(dict(registered_profiles=len(rows),distinct_backend_cohorts=len(cohorts),cohorts=list(cohorts.values()),profile_library_State_symbols=overlaps,symbol_inspection=dict(argv=cmd,returncode=child.returncode),resources=resources,identities=identities,State_writer_qualified=False,device_executed=False,application_replayed=False),indent=2))
