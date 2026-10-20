"""CPU-only: bind actual capture TTIR to the State source-use audit."""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
from triton._C.libtriton import ir
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
source=Path(__file__).parent
spec=importlib.util.spec_from_file_location('state_source_uses',source/'state_source_uses.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
registration=Path('/tmp/chijin-timeline-r087-gcu/runs/preservation-build-v5/output/actual-profiles/rows.json');registered=json.loads(registration.read_bytes());need(len(registered)==109,'Actual transform registration differs');rows=[];cache={}
for old in registered:
 row={k:old[k] for k in ['stage','case','capture_file','capture_sha256','math_file','math_sha256','before_sha256','after_sha256','binary_sha256','LLVM_sha256','original_before_file','original_after_file','actual_transform_arguments']};row.update(state_writer_qualified=False,native_timing_boundary_qualified=False)
 try:
  capfile=Path(row['capture_file']);mathfile=Path(row['math_file']);need(sha(capfile.read_bytes())==row['capture_sha256'] and sha(mathfile.read_bytes())==row['math_sha256'],'Original capture/math changed');cap=json.loads(capfile.read_bytes());math=json.loads(mathfile.read_bytes());ttir=cap['metadata']['compiled_snapshot']['compiler_artifacts']['ttir'];digest=sha(ttir.encode());need(digest==math['asm_sha256']['ttir'],'Actual source TTIR identity differs')
  need(sha(Path(row['original_before_file']).read_bytes())==row['before_sha256'] and sha(Path(row['original_after_file']).read_bytes())==row['after_sha256'],'Actual transform input/output changed')
  header=next(l for l in ttir.splitlines() if 'tt.func public' in l);names=re.findall(r'%([\w]+):\s*!tt.ptr<',header);need(names.count('State')==1,'Actual source State argument differs');function=re.search(r'@([\w.$-]+)\(',header)[1];state_index=names.index('State')
  if digest not in cache:
   folder=a.output/('object-'+str(len(cache)));folder.mkdir();inp=folder/'source.ttir';inp.write_text(ttir);context=ir.context();ir.load_dialects(context);module=ir.parse_mlir_module(str(inp),context);need(module.get_function(function).get_num_args()==len(names),'Source pointer ordinal requires all-pointer formal ABI');answer=helper.check_state_source_uses(module,function_name=function,state_index=state_index);cache[digest]=answer; (folder/'source-uses.json').write_text(json.dumps(answer,indent=2))
  answer=cache[digest];need(answer['state_address_noescape'] is True,'Original source pointer escape');admitted=old['status']=='original_GCU_program_projection_preserved';row.update(source_sha256=digest,source_uses=answer,status='source_noescape',transform_preserved=admitted,observer_payload_admitted=admitted)
  if admitted:
   certificate=Path(old['certificate_file']);proof=json.loads(certificate.read_bytes());need(sha(certificate.read_bytes())==old['certificate_sha256'],'Preservation certificate changed');need(all(proof.get(k) is True for k in ['original_program_preserved','observer_memory_isolated','actual_output_program_core_identical']) and proof['boundary']=='gcu_execution_ir_before_SDK_lowering','Preservation certificate scope differs');row.update(certificate_file=str(certificate),certificate_sha256=sha(certificate.read_bytes()))
 except (ValueError,KeyError,StopIteration,RuntimeError) as error:row.update(status='unverified',observer_payload_admitted=False,error=str(error))
 rows.append(row);(a.output/'rows.json').write_text(json.dumps(rows,indent=2))
(a.output/'result.json').write_text(json.dumps(dict(registered=109,checked=len(rows),distinct_sources=len(cache),source_noescape=sum(r['status']=='source_noescape' for r in rows),observer_payload_admitted=sum(r.get('observer_payload_admitted',False) for r in rows),failures=[r for r in rows if r['status']=='unverified'],state_writer_qualified=False,native_timing_boundary_qualified=False,device_executed=False,application_replayed=False),indent=2))
