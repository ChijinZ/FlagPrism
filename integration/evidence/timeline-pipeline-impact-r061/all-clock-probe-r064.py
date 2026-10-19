import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
from triton._C.libtriton import llvm
from triton.backends.nvidia.compiler import get_ptxas
from flagtree.profiler.timeline_nvidia_machine import counter_map
from flagtree.profiler.timeline_nvidia_control import _text_instructions,_bound_functions
from flagtree.profiler.timeline_nvidia_late_boundaries import _native_lines
root=Path('/workspace/chijin-timeline-r061-nvidia/runs/budget-pipeline-v1/output/device/profile/timeline');item=json.loads((root/'index.json').read_text())['captures'][0];cap=json.loads((root/item['capture_file']).read_text());plan=dict(cap['owner']['plan']);artifact=next(r for r in cap['metadata']['timeline_artifacts'] if r['retained_file'].endswith('.llir'));original=(root/artifact['retained_file']).read_text()
if hashlib.sha256(original.encode()).hexdigest()!=artifact['sha256']:raise RuntimeError('Original final LLVM changed')
ids={s['site_id'] for s in plan['sites'] if s['kind']=='matrix_issue_bracket'};changed=[];lines=[]
for line in original.splitlines(keepends=True):
 if 'flagprism_late_probe_site_' in line and 'mov.u64 $0, %globaltimer' in line:
  if line.count(',~{memory}"')!=1:raise RuntimeError('Unexpected clock reader constraints')
  line=line.replace(',~{memory}"','"');changed.append(line)
 lines.append(line)
if len(changed)!=sum(2 if s['record_semantics']=='observer_issue_bracket' else 1 for s in plan['sites']) or not ids:raise RuntimeError('Wrong changed reader count')
modified=''.join(lines);(a.output/'reference-original.ll').write_text(original);(a.output/'reference-modified.ll').write_text(modified);(a.output/'plan.json').write_text(json.dumps(plan,indent=2));llvm.init_targets();ptx=llvm.translate_to_asm(modified,'nvptx64-nvidia-cuda','sm_120a','+ptx88',['nvptx-mad-wide-opt'],True,False);ptx=re.sub(r',\s*debug|debug,\s*','',ptx);(a.output/'modified.ptx').write_text(ptx)
steps=[]
def run(name,cmd):
 with (a.output/(name+'.stdout')).open('xb') as out,(a.output/(name+'.stderr')).open('xb') as err:r=subprocess.run([str(x) for x in cmd],stdout=out,stderr=err,timeout=30)
 steps.append(dict(name=name,argv=[str(x) for x in cmd],returncode=r.returncode))
 if r.returncode:raise RuntimeError(name+' failed')
run('ptxas',[get_ptxas(120).path,'-lineinfo','-v','--gpu-name=sm_120a',a.output/'modified.ptx','-o',a.output/'modified.cubin']);tool=Path(sys.prefix)/'lib/python3.10/site-packages/nvidia/cu13/bin/nvdisasm'
for name,flags in [('lines',['--print-code','--print-line-info-ptx']),('json',['--emit-json'])]:run(name,[tool,*flags,a.output/'modified.cubin'])
labels,inst=_text_instructions((a.output/'lines.stdout').read_bytes());critical=[dict(section=s,pc=pc,opcode=o,predicate=p,operands=args) for (s,pc),(o,p,args) in sorted(inst.items()) if o.startswith(('LDGSTS','LDGDEPBAR','DEPBAR','BAR.','LDSM','HMMA','IMMA','MMA'))];bid=hashlib.sha256((a.output/'modified.cubin').read_bytes()).hexdigest();plan['binary_id']=bid;phases=[(s['site_id'],phase) for s in plan['sites'] for phase in (['entry','exit'] if s['record_semantics']=='observer_issue_bracket' else ['exit'])];machine=counter_map(cubin=(a.output/'modified.cubin').read_bytes(),ptx=ptx.encode(),sass_lines=(a.output/'lines.stdout').read_bytes(),sass_json=(a.output/'json.stdout').read_bytes(),binary_id=bid,scope_ids=tuple(s['site_id'] for s in plan['sites']),expected_sm=(12,0),marker_flavor='late-v1',expected_phases=phases);proof=[]
for i in ids:
 readers={x['phase']:x for x in machine['counter_pcs'] if x['site_id']==i};begin,end=readers['entry'],readers['exit'];ops=[x for x in critical if x['opcode'].startswith('HMMA') and x['section']=='.text.'+begin['function']];proof.append(dict(site_id=i,begin_reader_pc=begin['pc'],end_reader_pc=end['pc'],HMMA=[x['pc'] for x in ops],all_same_function_HMMA_between_readers=bool(ops) and all(begin['pc']<x['pc']<end['pc'] for x in ops)))
(a.output/'counter-map.json').write_text(json.dumps(machine,indent=2));(a.output/'result.json').write_text(json.dumps(dict(status='CPU_codegen_all_clock_reader_memory_clobber_probe_only',application_replayed=False,device_executed=False,shipping_implementation_changed=False,source_LLVM_sha256=artifact['sha256'],modified_LLVM_sha256=hashlib.sha256(modified.encode()).hexdigest(),changed_clock_reader_lines=changed,critical_native=critical,matrix_reader_checks=proof,steps=steps,source_cost_or_schedule_qualified=False),indent=2))
