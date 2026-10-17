"""Retained-byte audit only: never import product or execute device code locally."""
import hashlib,json,pathlib,tarfile
root=pathlib.Path(__file__).parent;old=root/'clock-objects-original'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_text())
r1=read(old/'runs/clock-scale-v1/terminal.json');r2=read(old/'runs/clock-scale-v2/terminal.json')
if r1['returncode']!=1 or r2['returncode']!=0:raise RuntimeError('Failure history or success changed')
r=read(old/'runs/clock-scale-v2/output/result.json');calls=r['calls'];reg=r['registration']
if len(calls)!=reg['requested_math_launches'] or len(calls)!=9:raise RuntimeError('Wrong call count')
if read(old/'runs/clock-scale-v2/output/capture.json')['math_executions_after_capture']!=0:raise RuntimeError('Capture executed math')
script=old/'clock-input-v2/p01_nvidia_clock_scale.py'
if sha(script.read_bytes())!=r2['script_sha256'] or sha(script.read_bytes())!=reg['source_sha256']:raise RuntimeError('Executed source changed')
if script.read_bytes()!=pathlib.Path('FlagPrism-method/tests/timeline/p01_nvidia_clock_scale.py').read_bytes():raise RuntimeError('Git candidate differs from executed input')
for index,c in enumerate(calls):
 if c['state']!=index+1 or c['runtime_k']!=reg['runtime_k'][index//3] or c['repetition']!=index%3:raise RuntimeError('Wrong math request ordering')
 delta=c['raw_end_tick']-c['raw_start_tick'];event=round(c['event_elapsed_ms']*1000000);allowance=max(10000,(event*2+99)//100)
 if delta!=c['tick_delta'] or delta!=c['candidate_internal_ns'] or event!=c['event_elapsed_ns_rounded'] or allowance!=c['event_allowance_ns']:raise RuntimeError('Arithmetic changed')
 if not 0<delta<=c['host_after_ns']-c['host_before_ns'] or abs(event-delta)>allowance:raise RuntimeError('Frozen scale consistency gate failed')
actual_clock_sha=sha((old/'runs/clock-scale-v2/output/clock-math.cubin').read_bytes())
if any(c['binary_sha256']!=actual_clock_sha for c in calls):raise RuntimeError('Call binary differs from actual retained cubin')
if sha((old/'clock-input-v1/p01_nvidia_clock_scale.py').read_bytes())!=r1['script_sha256']:raise RuntimeError('First-failure input changed')
for item in r['artifacts']:
 path=old/'runs/clock-scale-v2/output'/item['path']
 if sha(path.read_bytes())!=item['sha256'] or path.stat().st_size!=item['bytes']:raise RuntimeError('Compiled object changed')
inspection=old/'runs/object-inspection-v1/output';objects=read(inspection/'objects.json');summary=[]
with tarfile.open('artifacts/timeline/run-007/preflight/events-original-evidence.tgz') as t:
 cubins={pathlib.Path(m.name).parts[-2]:t.extractfile(m).read() for m in t.getmembers() if m.isfile() and 'runs/device-public-v2/output/api-cold/timeline/binaries/' in m.name and m.name.endswith('.cubin')}
for row in objects:
 i=row['index'];raw=(old/'runs/clock-scale-v2/output/clock-math.cubin').read_bytes() if i==2 else cubins[pathlib.Path(row['cubin']).parts[-2]]
 if sha(raw)!=row['sha256']:raise RuntimeError('Final machine object identity mismatch')
 for step in row['steps']:
  for stream in ['stdout','stderr']:
   if sha((inspection/(str(i)+'-'+step['kind']+'.'+stream)).read_bytes())!=step[stream+'_sha256']:raise RuntimeError('Tool output changed')
  if step['returncode']!=0 or '--no-dataflow' in step['argv']:raise RuntimeError('Actual full CFG/JSON/lines not obtained')
 meta,functions=read(inspection/(str(i)+'-json.stdout'))
 if meta['SM']['version']!={'major':12,'minor':0}:raise RuntimeError('Unexpected actual machine target')
 for f in functions:
  ins=f['sass-instructions'];counts={}
  for n,pred in [('globaltimer',lambda x:x.get('opcode')=='CS2R' and 'SR_GLOBALTIMERLO' in x.get('operands','')),('ffma',lambda x:x.get('opcode')=='FFMA'),('async_copy',lambda x:x.get('opcode','').startswith('LDGSTS')),('commit',lambda x:x.get('opcode')=='LDGDEPBAR'),('wait',lambda x:x.get('opcode','').startswith('DEPBAR'))]:counts[n]=sum(pred(x) for x in ins)
  if not counts['globaltimer']:raise RuntimeError('Actual timer getter not found')
  summary.append(dict(index=i,function=f['function-name'],cubin_sha256=row['sha256'],instructions=len(ins),machine_counts=counts,actual_compiler_metadata=meta))
state=read(root/'final-owned-state.json')
if any(x['live_owned_worker_group'] for x in state):raise RuntimeError('Live owned worker remains')
result={'status':'retained_bytes_and_clock_consistency_audited_not_clock_or_boundary_certified','source_sha256':reg['source_sha256'],'explicit_math_calls':len(calls),'binary_sha256':calls[0]['binary_sha256'],'state_after_capture':0,'event_minus_ticks_ns_range':[min(c['event_elapsed_ns_rounded']-c['tick_delta'] for c in calls),max(c['event_elapsed_ns_rounded']-c['tick_delta'] for c in calls)],'same_binary_all_calls':len({c['binary_sha256'] for c in calls})==1,'physical_record_bits':'raw integers retained, not float absolute ticks','final_objects':summary,'archives':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in [root/'clock-objects-original-evidence.tgz',root/'tools-installed-evidence.tgz',root/'disassembly-tools-original.tgz']},'limits':['device math assertions are reported by the executed harness, not rerun by this byte audit','static opcode counts do not certify site mapping, predication, completion, buffer identity or loss closure','9 graph calls validate this dedicated clock primitive, not public graph capture support or full P01','neither a fine-grained error bound nor a cross-SM epoch certificate']}
(root/'clock-objects-root-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','explicit_math_calls','same_binary_all_calls','event_minus_ticks_ns_range']}))
