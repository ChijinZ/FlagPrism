"""Registered retained ordinary/profile State partitions; no application replay."""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
input_root=Path(__file__).parent;module=input_root/'nvidia_state_writer_partition.py';spec=importlib.util.spec_from_file_location('state_check',module);checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
env=dict(os.environ,TORCH_DEVICE_BACKEND_AUTOLOAD='0');env.pop('PYTHONPATH',None)
for label,options in [('normal',[]),('optimized',['-O'])]:
 with (a.output/('fixtures-'+label+'.log')).open('xb') as log:
  child=subprocess.Popen([sys.executable,'-I',*options,'-m','pytest','-q',str(input_root/'test_nvidia_state_writer_partition.py'),'--basetemp',str(a.output/('pytest-'+label))],env=env,stdout=log,stderr=subprocess.STDOUT)
  try:code=child.wait(timeout=60)
  finally:
   if child.poll() is None:child.kill()
   child.wait(timeout=10)
 if code:raise RuntimeError('State fixture failed: '+label)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def need(value,message):
 if not value:raise ValueError(message)
cache={};rows=[];ordinary_refs={}
freeze_config=json.loads((input_root/'config.json').read_text())
def qualify(files,math,grid):
 header=next(line for line in files['ttgir'].read_text().splitlines() if 'tt.func public @' in line)
 args=re.findall(r'%([A-Za-z_][\w]*):\s*!tt.ptr<',header);need(args.count('State')==1,'Ambiguous State ABI')
 shape=math['shape'];elements=shape[0] if math['case'] in ('q01','q02','q03','q04') else shape[0]*shape[1]
 need(tuple(grid)[:len(math['grid'])]==tuple(math['grid']) and all(x==1 for x in tuple(grid)[len(math['grid']):]),'Launch geometry changed')
 key=(sha(files['ptx']),args.index('State'),math['config']['num_warps']*32,tuple(grid),elements)
 if key not in cache:cache[key]=checker.partition(files['ptx'].read_text(),state_argument=key[1],threads=key[2],grid=grid,elements=elements)
 return cache[key]
def check_once(math,path):
 need(math.get('requested_launches')==1 and math.get('input_immutable') is True and (math.get('state_unique_logical_index_pass') is True or math.get('state_count_passed') is True),'Original State/math launch checks not passed')
 marker=path.with_suffix('.host-once.json');once=json.loads(marker.read_text());need(once['requested_launches']==1,'Host-once marker differs')
 if 'pid' in math:need(once['pid']==math['pid'],'Host-once process differs')
 return dict(file=str(marker),sha256=sha(marker))
def check_ordinary(registered,kind):
 path=Path(registered['math_file']);need(sha(path)==registered['math_sha256'],'Ordinary report changed');math=json.loads(path.read_bytes());files={}
 for f in registered['artifacts']:
  obj=Path(f['path']);need(sha(obj)==f['sha256'],'Ordinary compiler object changed');files[f['kind']]=obj
 once=check_once(math,path)
 if kind != 'ordinary-runtime_K':ordinary_refs[registered['id']]=dict(file=str(path),sha256=sha(path),report=math)
 answer=qualify(files,math,registered['grid'])
 return dict(id=registered['id'],kind=kind,math_file=str(path),math_sha256=sha(path),compiled_hash=math['compiled_hash'],artifacts=registered['artifacts'],host_once=once,partition=answer)
inventory=json.loads(Path('/workspace/chijin-timeline-r078-nvidia/runs/state-inventory-v1/output/inventory.json').read_text())
for row in inventory['rows']:
 try:result=dict(status='pass',**check_ordinary(row,'ordinary-'+row['variant']))
 except (ValueError,KeyError,RuntimeError,StopIteration) as error:result=dict(status='unverified',id=row['id'],kind='ordinary-'+row['variant'],error=str(error))
 rows.append(result)
supp=Path('/workspace/chijin-timeline-r056-supplement-nvidia-v1');ordinary=supp/'runs/ordinary-v1/ordinary-result.json';supp_result=json.loads(ordinary.read_text());frozen=ordinary.with_name('ordinary-freeze.json');need(sha(frozen)==freeze_config['supplement_ordinary_freeze_sha256'],'Supplement ordinary freeze changed');bound=json.loads(frozen.read_text());need(sha(ordinary)==bound['ordinary_result_sha256'],'Supplement ordinary result changed')
for row in supp_result['rows']:
 try:
  path=Path(row['report']);need(sha(path)==row['report_sha256'],'Supplement frozen report changed');math=json.loads(path.read_bytes());artifacts=[]
  for key,wanted in math['asm_sha256'].items():
   matches=list(path.with_suffix('.objects').glob('*-'+key));need(len(matches)==1,'Supplement object ambiguity');obj=matches[0];need(sha(obj)==wanted,'Supplement object changed');artifacts.append(dict(kind=key,path=str(obj),sha256=wanted))
  result=dict(status='pass',**check_ordinary(dict(id=row['id'],math_file=str(path),math_sha256=row['report_sha256'],artifacts=artifacts,grid=math['grid']),'ordinary-supplement'))
 except (ValueError,KeyError,RuntimeError,StopIteration) as error:result=dict(status='unverified',id=row['id'],kind='ordinary-supplement',error=str(error))
 rows.append(result)
(a.output/'ordinary-checks.json').write_text(json.dumps(rows,indent=2))
from flagtree.profiler.timeline_capture_store import load_capture_file
profiles=json.loads((input_root/'profile-captures.json').read_text());profile_rows=[]
for registered in profiles:
 path=Path(registered['file'])
 try:
  need(sha(path)==registered['sha256'],'Original SQL registration capture changed');capture=load_capture_file(path);root=path.parent.parent;files={};artifacts=[]
  for f in capture['metadata']['timeline_artifacts']:
   obj=root/f['retained_file'];need(sha(obj)==f['sha256'],'Retained profile object changed');key=obj.suffix.lstrip('.')
   if key in ('ttgir','ptx','cubin'):
    need(key not in files,'Duplicate profile compiler artifact');files[key]=obj;artifacts.append(dict(kind=key,path=str(obj),sha256=f['sha256']))
  case=registered['case'];case_id=re.match(r'q\d+-s\d+-c\d+',case)[0]
  if registered['stage']=='retained-unit-repair-original-six':math_file=Path('/workspace/chijin-timeline-r055-qualification-nvidia-v2/runs/profile-first-v1')/case/'math.json'
  else:math_file=root.parent.parent/'math.json'
  math=json.loads(math_file.read_bytes())
  for key in ('ptx','cubin'):need(sha(files[key])==math['asm_sha256'][key],'Profile mathematical object differs from capture: '+key)
  reference=ordinary_refs[case_id];ordinary_math=reference['report'];need(sha(Path(reference['file']))==reference['sha256'],'Frozen ordinary reference changed')
  for key in ('shape','config','source_sha256','input_sha256'):
   need(math[key]==ordinary_math[key],'Profile differs from frozen ordinary mathematics: '+key)
  if 'runtime_k' in ordinary_math:need(math['runtime_k']==ordinary_math['runtime_k'],'Profile runtime K changed')
  once=check_once(math,math_file)
  launch_grid=capture['owner']['layout']['grid'];answer=qualify(files,math,launch_grid)
  profile_rows.append(dict(status='pass',case=case,stage=registered['stage'],capture_file=str(path),capture_sha256=sha(path),math_file=str(math_file),math_sha256=sha(math_file),binary_id=capture['owner']['binary_id'],compiled_hash=math['compiled_hash'],artifacts=artifacts,host_once=once,ordinary_reference=dict(file=reference['file'],sha256=reference['sha256']),partition=answer))
 except (ValueError,KeyError,RuntimeError,StopIteration) as error:profile_rows.append(dict(status='unverified',case=registered['case'],stage=registered['stage'],capture_file=str(path),error=str(error)))
 (a.output/'profile-checks.json').write_text(json.dumps(profile_rows,indent=2))
summary=dict(status='registered_retained_nvidia_state_partitions',ordinary_registered=40,ordinary_checked=len(rows),ordinary_passed=sum(r['status']=='pass' for r in rows),profile_registered=len(profiles),profile_checked=len(profile_rows),profile_passed=sum(r['status']=='pass' for r in profile_rows),distinct_partitions=len(cache),failures=[r for r in rows+profile_rows if r['status']!='pass'],checker_sha256=sha(module),source_loaded_qualification_tool=True,product_runtime_changed=False,device_executed=False,application_replayed=False)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if summary['ordinary_passed']!=40 or summary['profile_passed']!=len(profiles):raise RuntimeError('Some registered State partitions remain unverified')
