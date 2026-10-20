"""Actual retained supplemental ordinary callers; passive CPU codegen only."""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys
from collections import Counter
from pathlib import Path
from flagtree.profiler._deadline import _stop_worker
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inp=Path(__file__).parent
spec=importlib.util.spec_from_file_location('ascend_state',inp/'ascend_state_writer_partition.py');checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
inv=json.loads((inp/'inventory.json').read_bytes());need(len(inv['rows'])==8,'Supplement ordinary registration count differs');freeze=Path(inv['freeze_file']);frozen=json.loads(freeze.read_bytes());need(sha(freeze)==inv['freeze_sha256'] and sha(frozen['ordinary_result'])==frozen['ordinary_result_sha256'],'Frozen ordinary registration changed');need([r['id'] for r in frozen['rows']]==[r['id'] for r in inv['rows']],'Frozen ordinary IDs differ');rows=[];cache={};objects=a.output/'objects';objects.mkdir()
for index,row in enumerate(inv['rows']):
 result=dict(id=row['id'],math_file=row['math_file'],math_sha256=row['math_sha256'],state_writer_qualified=False)
 try:
  mathfile=Path(row['math_file']);need(sha(mathfile)==row['math_sha256'],'Frozen ordinary math changed');math=json.loads(mathfile.read_bytes());marker=mathfile.with_suffix('.host-once.json');host=json.loads(marker.read_bytes());need(host['requested_launches']==math['requested_launches']==1 and math['state_count_passed'] is True and math['input_immutable'] is True and math['guards_passed'] is True,'Original math/guard/once checks failed');artifacts={x['kind']:Path(x['path']) for x in row['artifacts']}
  for art in row['artifacts']:need(sha(art['path'])==art['sha256']==math['asm_sha256'][art['kind']],'Original compiler artifact changed')
  metadata_file,=(mathfile.parent.parent/'cache'/row['id']).rglob(math['case']+'.json');meta=json.loads(metadata_file.read_bytes());need(meta['hash']==math['compiled_hash'] and meta['arch']=='Ascend910B4-1' and meta['enable_auto_blockify'] is False and meta['force_simt_only'] is False and meta['parallel_mode']=='simd','Actual ordinary launch ABI differs');key=(sha(artifacts['bcmlir']),sha(artifacts['npubin']));bound=cache.get(key)
  if bound is None:
   folder=a.output/('object-'+str(index));cmd=[sys.executable,'-I',str(inp/'row.py'),'--row-index',str(index),'--output',str(folder)]
   with (a.output/('object-'+str(index)+'.stdout')).open('xb') as out,(a.output/('object-'+str(index)+'.stderr')).open('xb') as err:
    child=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True,env=dict(os.environ,ASCEND_RT_VISIBLE_DEVICES='',CHIJIN_PASSIVE_OBJECT_ROOT=str(objects)))
    try:child.wait(timeout=65)
    except BaseException:_stop_worker(child);raise
   need(child.returncode==0,'Actual passive codegen failed; retain child receipts');proof=json.loads((folder/'result.json').read_bytes());need(proof['original_npubin_sha256']==key[1] and any(p['whole_binary_identical'] for p in proof['produced']),'Actual codegen did not reproduce original whole binary');bound=dict(file=str(folder/'result.json'),sha256=sha(folder/'result.json'),proof=proof);cache[key]=bound
  need(sha(bound['file'])==bound['sha256'],'Actual codegen receipt changed');jobs=[]
  for name in bound['proof']['codegen_receipts']:
   jobfile=Path(name);job=json.loads(jobfile.read_bytes())
   if '--cce-aicore-only' not in job['argv']:continue
   need(job['state']=='finished' and job['exit']==0,'Actual code generator did not finish');units=[]
   for entry in job['inputs']:
    if not entry['path'].endswith('.ll'):continue
    kept=Path(entry['retained_file']);need(kept.is_absolute() and sha(kept)==entry['sha256'],'Retained actual LLVM input changed');text=kept.read_text();functions=[m[0] for m in re.finditer(r'^define dso_local void @[^\n]+\{\n.*?^}',text,re.M|re.S)];need(functions,'Actual actor function missing');units.append(dict(path=str(kept),sha256=entry['sha256'],functions=functions))
   need(units,'Actual codegen LLVM inputs missing');jobs.append(dict(argv=job['argv'],receipt_file=str(jobfile),receipt_sha256=sha(jobfile),inputs=job['inputs'],units=units))
  has_cube=any('--cce-aicore-arch=dav-c220-cube' in job['argv'] for job in jobs);need((meta['mix_mode'],meta['bs_task_type'])==(('mix',32) if has_cube else ('aiv',10)),'Actual actor functions/task launch metadata differ');header=next(l for l in artifacts['ttir'].read_text().splitlines() if 'tt.func public @' in l);formals=re.findall(r'%([A-Za-z_][\w]*):\s*!tt.ptr<',header);need(formals.count('State')==1,'Actual frontend State formal absent');aggregate=Counter();parts=[]
  for job in jobs:
   actor='AIC' if '--cce-aicore-arch=dav-c220-cube' in job['argv'] else 'AIV';subblocks=meta['bs_task_type']%10 if actor=='AIV' and has_cube else 1
   for unit in job['units']:
    for body in unit['functions']:
     parameters=checker._parse(body)[0];ptrs=[v for v,t in parameters.items() if t.startswith('ptr')];need(len(ptrs)-len(formals)==2,'Actual user/hidden argument prefix ABI differs');state=ptrs[2+formals.index('State')];partition=checker.analyze(body,state_parameter=state,grid_parameters=list(parameters)[-3:],grid=math['grid'],subblocks=subblocks,elements=math['math']['count']);aggregate.update(partition['element_writers']);parts.append(dict(actor=actor,source_file=unit['path'],source_sha256=unit['sha256'],State_formal=state,grid_parameters=list(parameters)[-3:],subblocks=subblocks,partition=partition))
  need(len(aggregate)==math['math']['count'] and all(aggregate[i]==1 for i in range(math['math']['count'])),'Combined actual actor State writers overlap or omit');result.update(status='partition_under_reviewed_SDK_model',elements=math['math']['count'],grid=math['grid'],host_once_file=str(marker),host_once_sha256=sha(marker),metadata_file=str(metadata_file),metadata_sha256=sha(metadata_file),original_npubin_sha256=key[1],original_bcmlir_sha256=key[0],codegen=bound,parts=parts,jobs=jobs)
 except (ValueError,KeyError,StopIteration) as error:
  detail=[];tb=error.__traceback__
  while tb is not None:
   if tb.tb_frame.f_code.co_filename==str(inp/'ascend_state_writer_partition.py') and 'op' in tb.tb_frame.f_locals:detail.append(str(tb.tb_frame.f_locals['op']))
   tb=tb.tb_next
  result.update(status='unverified',error=str(error),necessary_instruction_context=detail[-1:])
 rows.append(result);(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
summary=dict(status='supplementary8_Ascend_State_partition',registered=8,checked=len(rows),partitioned=sum(r['status']!='unverified' for r in rows),distinct_CPU_codegen=len(cache),checker_sha256=sha(inp/'ascend_state_writer_partition.py'),freeze_sha256=sha(freeze),failures=[r for r in rows if r['status']=='unverified'],state_writer_qualified=False,SDK_ABI_binding_qualified=False,native_timing_boundary_qualified=False,device_executed=False,application_replayed=False);(a.output/'result.json').write_text(json.dumps(summary,indent=2));need(summary['partitioned']==8,'Supplementary State coverage incomplete')
