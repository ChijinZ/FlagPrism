"""Reuse the frozen State checker on retained profiling objects, without replay."""
import argparse, base64, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
def need(ok,message):
 if not ok:raise ValueError(message)
def sha(value):return hashlib.sha256(value).hexdigest()
def read(path):return Path(path).read_bytes()
helper=Path('/tmp/chijin-timeline-r082-gcu/State-partition-input-v4/gcu_state_writer_partition.py')
need(sha(read(helper))=='7aeadcab3ecb2e6e64f37fb86d8479cf88f3400de7cd5d5d33dc998810e2102e','Frozen checker changed')
spec=importlib.util.spec_from_file_location('gcu_state',helper);checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
roots=[('original-six','/tmp/chijin-timeline-r052-qualification-profile-v1/runs/profile-first-v1',72),('supplement','/tmp/chijin-timeline-r054-supplement-profile-v1/runs/profile-first-v1',24),('affected','/tmp/chijin-timeline-r055-qualification-gcu-affected-v1/runs/affected-v1',13)]
tool=Path('/opt/triton_gcu/bin/gcu-compiler-translate');need(sha(read(tool))=='f93024f7d86828022bc6b61d77c02522195d25df5ad76ac634d909efe74bb361','Translator changed')
cache={};translated={};rows=[]
for stage,root,count in roots:
 indices=sorted(Path(root).rglob('timeline/index.json'));need(len(indices)==count,'Registered stage capture count differs: '+stage)
 for index in indices:
  ix=json.loads(read(index));need(len(ix['captures'])==1,'Expected registered single-capture mathematical call')
  entry=ix['captures'][0];path=index.parent/entry['capture_file'];capture=json.loads(read(path));mathpath=index.parents[2]/'math.json';math=json.loads(read(mathpath));row=dict(stage=stage,case=index.parents[2].name,capture_file=str(path),capture_sha256=sha(read(path)),math_file=str(mathpath),math_sha256=sha(read(mathpath)),state_writer_qualified=False)
  try:
   meta=capture['metadata'];snapshot=meta['compiled_snapshot'];binary=base64.b64decode(snapshot['binary_base64'],validate=True);need('asm_sha256' in math and 'fatbin' in math['asm_sha256'],'This math receipt needs its separate profiling-object binding');need(sha(binary)==math['asm_sha256']['fatbin'] and snapshot['executable']['binary_sha256']==sha(binary) and capture['owner']['binary_id']==math['compiled_hash'],'Math-bound loaded binary differs')
   need(math['requested_launches']==1 and math['input_immutable'] is True and math['state_unique_logical_index_pass'] is True,'Original mathematical call did not pass host-once checks')
   artifacts=snapshot['compiler_artifacts'];llir=artifacts['llir'];ttir=artifacts['ttir'];source_sha=sha(llir.encode());ttir_sha=sha(ttir.encode());need(source_sha==math['asm_sha256']['llir'] and ttir_sha==math['asm_sha256']['ttir'],'Math-bound compiler input differs')
   header=next(l for l in ttir.splitlines() if 'tt.func public' in l);names=re.findall(r'%([\w]+):\s*!tt.ptr<',header);need(names.count('State')==1,'Actual State formal missing');function=re.search(r'@([\w.$-]+)\(',header)[1]
   previous=Path('/tmp/chijin-timeline-r083-gcu/runs/profile-State-v2/output')/source_sha
   if source_sha not in translated and (previous/'functions.ll').exists():
    need(sha(read(previous/'original.mlir'))==source_sha,'Retained previous translation input differs');translated[source_sha]=previous/'functions.ll'
   if source_sha not in translated:
    folder=a.output/source_sha;folder.mkdir();lines=llir.strip().splitlines();need(lines[0].startswith('"builtin.module"() ({') and lines[1].lstrip().startswith('"gpu.module"() ') and lines[-2].strip().startswith('})') and lines[-1].strip().startswith('})'),'Unknown module wrapper')
    original=folder/'original.mlir';original.write_text(llir);inp=folder/'functions.mlir';inp.write_text('"builtin.module"() ({\n'+'\n'.join(lines[2:-2])+'\n}) : () -> ()\n');output=folder/'functions.ll'
    with (folder/'stdout.log').open('xb') as so,(folder/'stderr.log').open('xb') as se:cp=subprocess.run([str(tool),'--mlir-to-llvmir',str(inp),'-o',str(output)],stdout=so,stderr=se,timeout=25)
    need(cp.returncode==0,'Actual profile LLVM translation failed');translated[source_sha]=output
   llvm=translated[source_sha];functions={m[1]:m[0] for m in re.finditer(r'^define[^\n]+@([\w.$-]+)\([^\n]*\)[^{\n]*\{\n.*?^}',llvm.read_text(),re.M|re.S)}
   params,ops,_,_,_=checker._parse(functions[function]);need(len(ops)==2 and ops[1]['operation']=='ret void','Unsupported external forwarding wrapper');callee,args=checker._call(ops[0]['operation']);need(args==['ptr '+v for v in params] and len(params)==len(names),'Actual user/hidden argument forwarding differs');internal=checker._parse(functions[callee])[0];need(len(internal)==len(params),'Internal formal ABI differs');state=list(internal)[names.index('State')]
   warps=re.search(r'"ttg.num-warps" = (\d+) : i32',llir);need(warps and re.search(r'"ttg.threads-per-warp" = 1 : i32',llir),'Physical thread metadata absent');threads=int(warps[1]);need(threads==math['config']['num_warps'],'Actual launch thread count differs')
   elements=math['math']['count'];grid=capture['owner']['layout']['grid'];need(tuple(grid[:len(math['grid'])])==tuple(math['grid']) and all(x==1 for x in grid[len(math['grid']):]),'Math/capture launch geometry differs')
   key=(source_sha,state,threads,tuple(grid),elements)
   if key not in cache:cache[key]=checker.analyze(functions[callee],state_parameter=state,grid=grid,threads=threads,elements=elements)
   answer=cache[key];counts=answer['element_writers'];need(len(counts)==elements and all(counts[i]==1 for i in range(elements)),'State writer partition differs')
   row.update(status='partition_under_frozen_SDK_model',source_sha256=source_sha,ttir_sha256=ttir_sha,LLVM_file=str(llvm),LLVM_sha256=sha(read(llvm)),binary_sha256=sha(binary),State_formal=state,threads=threads,grid=grid,elements=elements,partition=answer)
  except (ValueError,KeyError,StopIteration) as error:
   detail=[];tb=error.__traceback__
   while tb is not None:
    if tb.tb_frame.f_code.co_filename==str(helper) and 'op' in tb.tb_frame.f_locals:detail.append(str(tb.tb_frame.f_locals['op']))
    tb=tb.tb_next
   row.update(status='unverified',error=str(error),necessary_instruction_context=detail[-1:] )
  rows.append(row);(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
summary=dict(status='profile_State_applicability_inventory',registered=109,checked=len(rows),partitioned=sum(r['status']!='unverified' for r in rows),distinct_translations=len(translated),distinct_partitions=len(cache),failures=[r for r in rows if r['status']=='unverified'],state_writer_qualified=False,SDK_ABI_binding_qualified=False,vendor_final_IR=False,device_executed=False,application_replayed=False)
(a.output/'result.json').write_text(json.dumps(summary,indent=2))
