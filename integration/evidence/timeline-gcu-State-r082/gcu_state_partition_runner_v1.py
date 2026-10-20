"""Apply finite State transfer models to registered byte-bound LLVM inputs."""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inputs=Path(__file__).parent
spec=importlib.util.spec_from_file_location('gcu_state_check',inputs/'gcu_state_writer_partition.py');checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
def need(value,message):
 if not value:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for label,flags in [('normal',[]),('optimized',['-O'])]:
 with (a.output/('fixtures-'+label+'.log')).open('xb') as log:
  child=subprocess.Popen([sys.executable,'-I',*flags,'-m','pytest','-q',str(inputs/'test_gcu_state_writer_partition.py'),'--basetemp',str(a.output/('pytest-'+label))],stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0'))
  try:code=child.wait(timeout=35)
  finally:
   if child.poll() is None:child.kill()
   child.wait(timeout=10)
 if code:raise RuntimeError('State fixture failure: '+label)
root=Path('/tmp/chijin-timeline-r078-gcu/runs/state-inventory-v1/output');inventory=json.loads((root/'inventory.json').read_bytes());translated_root=Path('/tmp/chijin-timeline-r082-gcu/runs/translate-v3/output');translation=json.loads((translated_root/'rows.json').read_bytes());rows=[]
need(len(translation)==len(inventory['rows']),'Actual translation registration differs')
for row,trans in zip(inventory['rows'],translation):
 try:
  need((row['id'],row['variant'],row['math_sha256'])==(trans['id'],trans['variant'],trans['math_sha256']),'Actual translation identity differs');need(sha(Path(row['math_file']))==row['math_sha256'],'Original math report changed');math=json.loads(Path(row['math_file']).read_bytes());elements=math['math']['count']
  need(sha(Path(trans['translation_result']))==trans['translation_result_sha256'],'Translation receipt changed');llvm=Path(trans['LLVM_file']);need(sha(llvm)==trans['LLVM_sha256'],'Translated operation view changed')
  source=next(x for x in row['artifacts'] if x['kind']=='llir');need(source['sha256']==trans['source_sha256'] and sha(root/source['retained_file'])==source['sha256'],'Actual original SDK input differs')
  ttir=next(x for x in row['artifacts'] if x['kind']=='ttir');ttir_file=root/ttir['retained_file'];need(sha(ttir_file)==ttir['sha256'],'Original State frontend ABI changed');header=next(l for l in ttir_file.read_text().splitlines() if 'tt.func public' in l);user_args=re.findall(r'%([\w]+):\s*!tt.ptr<',header);need(user_args.count('State')==1,'Missing original State parameter');entry=re.search(r'@([\w.$-]+)\(',header)[1]
  functions={m[1]:m[0] for m in re.finditer(r'^define[^\n]+@([\w.$-]+)\([^\n]*\)[^{\n]*\{\n.*?^}',llvm.read_text(),re.M|re.S)}
  params,ops,_,_,_=checker._parse(functions[entry]);need(len(ops)==2 and ops[1]['operation']=='ret void','Unknown external wrapper body');callee,arguments=checker._call(ops[0]['operation']);need(len(params)==len(arguments)==len(user_args),'External formal ABI differs')
  need(arguments==['ptr '+p for p in params],'Actual wrapper must forward user arguments unchanged');body=functions[callee];internal=checker._parse(body)[0];need(len(internal)==len(params),'Internal formal ABI differs');state=list(internal)[user_args.index('State')]
  warps=re.search(r'"ttg.num-warps" = (\d+) : i32',(root/source['retained_file']).read_text());need(warps and re.search(r'"ttg.threads-per-warp" = 1 : i32',(root/source['retained_file']).read_text()),'Actual physical thread metadata absent');threads=int(warps[1]);need(threads==row['config']['num_warps'],'Original launch threads differ')
  partition=checker.analyze(body,state_parameter=state,grid=row['grid'],threads=threads,elements=elements);counts=partition['element_writers'];need(len(counts)==elements and all(counts[i]==1 for i in range(elements)),'Actual element partitions omit or overlap')
  rows.append(dict(id=row['id'],variant=row['variant'],status='partition_under_explicit_SDK_transfer_model',elements=elements,math_sha256=row['math_sha256'],source_sha256=source['sha256'],LLVM_sha256=trans['LLVM_sha256'],npubin_or_fatbin_sha256=trans['whole_binary_sha256'],State_formal=state,physical_threads=threads,partition=partition,state_writer_qualified=False))
 except (ValueError,KeyError,StopIteration) as error:rows.append(dict(id=row['id'],variant=row['variant'],status='unverified',error=str(error)))
 (a.output/'rows.json').write_text(json.dumps(rows,indent=2))
summary=dict(status='registered_State_ranges_under_explicit_GCU_SDK_model',checked=len(rows),partitioned=sum(r['status']!='unverified' for r in rows),registered=len(inventory['rows']),failures=[r for r in rows if r['status']=='unverified'],checker_sha256=sha(inputs/'gcu_state_writer_partition.py'),state_writer_qualified=False,vendor_final_IR=False,device_executed=False,application_replayed=False)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if summary['partitioned']!=summary['registered']:raise RuntimeError('Keep unverified original State partitions')
