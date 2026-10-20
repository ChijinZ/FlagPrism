"""Bounded CPU-only original codegen inventory; no math/device replay."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
root=Path(__file__).parent;config=json.loads((root/'config.json').read_bytes());inventory_file=Path('/tmp/chijin-timeline-r078-ascend/runs/state-inventory-v1/output/inventory.json')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if sha(inventory_file)!=config['inventory_sha256']:raise ValueError('Original retained inventory changed')
inventory=json.loads(inventory_file.read_bytes());rows=[];cache={};objects=a.output/'objects';objects.mkdir()
previous=Path('/tmp/chijin-timeline-r079-ascend/runs/ordinary-lowering-v1/output');prev_result=previous/'result.json';prev=json.loads(prev_result.read_bytes());prev_command=json.loads((previous/'command.json').read_bytes())
if not any(x['whole_binary_identical'] and sha(Path(x['path']))==prev['original_npubin_sha256'] for x in prev['produced']):raise ValueError('Original successful reproduction changed')
cache[(prev_command['source_sha256'],prev['original_npubin_sha256'])]=dict(result_file=str(prev_result),result_sha256=sha(prev_result),reused_from='r079 byte-identical original q03')
spec=importlib.util.spec_from_file_location('owned_probe_deadline','/tmp/chijin-timeline-r019/input/Profiler/python/flagtree_profiler/_deadline.py');deadline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=deadline;spec.loader.exec_module(deadline)
started=time.monotonic();new_compiles=0
for index,row in enumerate(inventory['rows']):
    math_file=Path(row['math_file'])
    if sha(math_file)!=row['math_sha256']:raise ValueError('Frozen mathematical report changed')
    artifacts={x['kind']:x for x in row['artifacts']}
    for kind in ('bcmlir','npubin'):
        if sha(inventory_file.parent/artifacts[kind]['retained_file'])!=artifacts[kind]['sha256']:raise ValueError('Frozen original compiler artifact changed')
    key=tuple(artifacts[k]['sha256'] for k in ('bcmlir','npubin'))
    bound=cache.get(key);status='unverified';child_code=None
    if bound:
        if sha(Path(bound['result_file']))!=bound['result_sha256']:raise ValueError('Reused codegen evidence changed')
        status='bound'
    else:
        folder=a.output/('row-'+str(index));command=[sys.executable,'-I',str(root/'row.py'),'--row-index',str(index),'--output',str(folder)]
        env=dict(os.environ,CHIJIN_PASSIVE_OBJECT_ROOT=str(objects),ASCEND_RT_VISIBLE_DEVICES='')
        with (a.output/('row-'+str(index)+'.stdout')).open('xb') as out,(a.output/('row-'+str(index)+'.stderr')).open('xb') as err:
            child=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True)
            try:child_code=child.wait(timeout=60)
            except BaseException:
                deadline._stop_worker(child);raise
        new_compiles+=1
        result_file=folder/'result.json'
        if result_file.is_file():
            result=json.loads(result_file.read_bytes())
            if child_code==0 and result['original_npubin_sha256']==key[1] and any(p['whole_binary_identical'] for p in result['produced']):
                bound=dict(result_file=str(result_file),result_sha256=sha(result_file),reused_from=None);cache[key]=bound;status='bound'
    rows.append(dict(index=index,id=row['id'],variant=row['variant'],math_file=str(math_file),math_sha256=row['math_sha256'],grid=row['grid'],config=row['config'],shape=row['shape'],compiled_hash=row['compiled_hash'],bcmlir_sha256=key[0],npubin_sha256=key[1],status=status,codegen=bound,child_exit=child_code,state_writer_qualified=False))
    (a.output/'rows.json').write_text(json.dumps(rows,indent=2));(a.output/'progress.json').write_text(json.dumps(dict(checked=len(rows),bound=sum(r['status']=='bound' for r in rows),new_CPU_compiles=new_compiles,elapsed_s=time.monotonic()-started),indent=2))
summary=dict(status='original_ordinary_byte_bound_codegen_inputs',registered=len(inventory['rows']),checked=len(rows),bound=sum(r['status']=='bound' for r in rows),distinct_bound_code_objects=len(cache),new_CPU_compiles=new_compiles,reused_rows=len(rows)-new_compiles,elapsed_s=time.monotonic()-started,device_executed=False,mathematical_application_replayed=False,SDK_rebuilt=False,product_runtime_changed=False,state_writer_qualified=False)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
if summary['bound']!=summary['registered']:raise RuntimeError('Some original compiler inputs remain unbound; retain failures')
