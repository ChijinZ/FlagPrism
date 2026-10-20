"""Registered original actor/caller State ranges; no mathematical replay."""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys
from collections import Counter
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);input_root=Path(__file__).parent
spec=importlib.util.spec_from_file_location('ascend_state_check',input_root/'ascend_state_writer_partition.py');checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
def need(value,message):
 if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for label,flags in [('normal',[]),('optimized',['-O'])]:
 with (a.output/('fixtures-'+label+'.log')).open('xb') as out:
  child=subprocess.Popen([sys.executable,'-I',*flags,'-m','pytest','-q',str(input_root/'test_ascend_state_writer_partition.py'),'--basetemp',str(a.output/('pytest-'+label))],stdout=out,stderr=subprocess.STDOUT,env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0'))
  try:code=child.wait(timeout=35)
  finally:
   if child.poll() is None:child.kill()
   child.wait(timeout=10)
 if code:raise RuntimeError('Finite State fixtures failed: '+label)
r=Path('/tmp/chijin-timeline-r078-ascend/runs/state-inventory-v1/output');inv=json.loads((r/'inventory.json').read_bytes());bound=Path('/tmp/chijin-timeline-r080-ascend/runs/ordinary-lowering-v1/output');references=json.loads((bound/'rows.json').read_bytes());callers=json.loads((input_root/'callers.json').read_bytes());rows=[]
for registered,reference in zip(inv['rows'],references):
 try:
  need(reference['status']=='bound' and reference['math_sha256']==registered['math_sha256'],'Original byte binding differs')
  math_file=Path(registered['math_file']);need(sha(math_file)==registered['math_sha256'],'Original mathematical report changed');math=json.loads(math_file.read_bytes());elements=math['math']['count'];need(type(elements)is int and elements>0,'Frozen oracle output/State extent')
  artifact=next(x for x in registered['artifacts'] if x['kind']=='ttir');ttir=r/artifact['retained_file'];need(sha(ttir)==artifact['sha256'],'Original frontend ABI changed')
  header=next(l for l in ttir.read_text().splitlines() if 'tt.func public @' in l);formals=re.findall(r'%([A-Za-z_][\w]*):\s*!tt.ptr<',header);need(formals.count('State')==1,'Missing frozen State formal')
  evidence=reference['codegen'];result_file=Path(evidence['result_file']);need(sha(result_file)==evidence['result_sha256'],'Byte-identical codegen receipt changed');source=next(x for x in callers if x['result_file']==str(result_file));need(source['npubin_sha256']==reference['npubin_sha256'],'Original caller/binary association changed');has_cube=any('--cce-aicore-arch=dav-c220-cube' in job['argv'] for job in source['jobs']);aggregate=Counter();parts=[]
  for job in source['jobs']:
   actor='AIC' if '--cce-aicore-arch=dav-c220-cube' in job['argv'] else 'AIV';subblocks=2 if actor=='AIV' and has_cube else 1
   for unit in job['sources']:
    kept=Path(unit['path']);need(sha(kept)==unit['sha256'],'Actual captured caller changed');lines=kept.read_text().splitlines()
    for function in unit['functions']:
     body=function['text'];start=function['line']-1;need(chr(10).join(lines[start:start+len(body.splitlines())])==body,'Caller excerpt differs from actual codegen input')
     parameters=checker._parse(body)[0];ptrs=[p for p,ty in parameters.items() if ty.startswith('ptr')];need(len(ptrs)-len(formals)==2,'Unknown original hidden GM prefix ABI');state_parameter=ptrs[2+formals.index('State')];grid_parameters=list(parameters)[-3:]
     partition=checker.analyze(body,state_parameter=state_parameter,grid_parameters=grid_parameters,grid=registered['grid'],subblocks=subblocks,elements=elements)
     aggregate.update(partition['element_writers']);parts.append(dict(actor=actor,source_sha256=unit['sha256'],state_parameter=state_parameter,grid_parameters=grid_parameters,subblocks=subblocks,partition=partition))
  need(len(aggregate)==elements and all(aggregate[i]==1 for i in range(elements)),'Combined actual actor State ranges overlap or omit elements')
  rows.append(dict(status='partition_under_inspected_transfer_and_actor_ABI_model',id=registered['id'],variant=registered['variant'],math_file=str(math_file),math_sha256=registered['math_sha256'],elements=elements,npubin_sha256=reference['npubin_sha256'],parts=parts,physical_transfer_ABI_qualification_pending=True))
 except (ValueError,KeyError,StopIteration) as error:
  rows.append(dict(status='unverified',id=registered['id'],variant=registered['variant'],error=str(error)))
 (a.output/'rows.json').write_text(json.dumps(rows,indent=2))
summary=dict(status='registered_ordinary_state_ranges_under_explicit_ABI_model',checked=len(rows),registered=len(inv['rows']),partitioned=sum(x['status']!='unverified' for x in rows),failures=[r for r in rows if r['status']=='unverified'],checker_sha256=sha(input_root/'ascend_state_writer_partition.py'),state_writer_qualified=False,device_executed=False,mathematical_application_replayed=False,source_loaded_qualification_tool=True)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if summary['partitioned']!=summary['registered']:raise RuntimeError('Some actual State ranges remain unverified')
