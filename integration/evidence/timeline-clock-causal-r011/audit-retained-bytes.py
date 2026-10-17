"""Retained bytes/causal algebra only; no product import or workstation oracle."""
import argparse,hashlib,json,struct,tarfile,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive',type=Path,default=Path(__file__).with_name('causal-final-original-evidence.tgz'))
p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4]/'FlagPrism-method')
p.add_argument('--output',type=Path,default=Path(__file__).with_name('causal-root-audit.json'))
a=p.parse_args()
with tarfile.open(a.archive) as t:fs={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
def need(v,m):
 if not v:raise RuntimeError(m)
def j(n):return json.loads(fs[n])
need(fs['installed-clock-module.py']==(a.repo/'Profiler/python/flagtree_profiler/timeline_clock.py').read_bytes(),'Installed common module bytes differ from source freeze')
for n in ['package-causal']:
 d=j(n+'/terminal.json');need(d['state']=='build_passed_not_device_qualified','Package failed')
 bridge=j(n+'/native-byte-bridge.json');need(bridge['byte_equal'] and len(bridge['native_members'])==7,'Changed native bytes')
need(j('runs/install-v1/output/result.json')['installed_members_byte_verified']==607,'Wheel installation identity')
for mode in ['normal','optimized']:
 log=fs['runs/install-v1/output/causal-clock-'+mode+'.stderr.log']
 need(b'Ran 9 tests' in log and b'\nOK\n' in log,'New algebra CPU contracts')
 result=j('runs/install-v1/output/clock-arithmetic-'+mode+'.json')
 need(result['count']==27 and not result['physical_clock_proof'],'Old clock arithmetic')
need(j('runs/clock-causal-v1/terminal.json')['returncode']==1 and b'unsupported AST node type: Break' in fs['runs/clock-causal-v1/stderr.log'],'First baseline failure lost')
need(j('runs/clock-causal-object-v1/terminal.json')['returncode']==1 and b'Unknown option' in fs['runs/clock-causal-object-v1/output/cfg.stderr'],'First tool failure lost')
summary=[];static=[];text_sections=[]
def section(raw,name):
 off=struct.unpack_from('<Q',raw,40)[0];stride,count,names=struct.unpack_from('<HHH',raw,58)
 hs=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
 strings=raw[hs[names][4]:hs[names][4]+hs[names][5]]
 h=[h for h in hs if strings[h[0]:].split(b'\0',1)[0].decode()==name]
 need(len(h)==1,'Missing unique actual ELF section')
 h=h[0];return raw[h[4]:h[4]+h[5]]
for version in [2,3]:
 prefix=f'runs/clock-causal-v{version}/output/'
 need(j(f'runs/clock-causal-v{version}/terminal.json')['returncode']==0,'Math acquisition failed')
 data=j(prefix+'result.json');calls=data['calls'];reg=data['registration']
 need(reg['rounds']==64 and reg['explicit_math_launches']==len(calls)==3,'Changed registered denominator')
 source=fs[f'causal-input-v{version}/p01_nvidia_clock_handshake.py']
 need(hashlib.sha256(source).hexdigest()==reg['source_sha256'],'Executed source SHA')
 if version==3:need(source==(a.repo/'tests/timeline/p01_nvidia_clock_handshake.py').read_bytes(),'Final executed script differs')
 artifacts={r['path']:r for r in data['artifacts']}
 for n,v in artifacts.items():need(hashlib.sha256(fs[prefix+n]).hexdigest()==v['sha256'],'Actual compiled artifact SHA')
 cubin=fs[prefix+'exchange.cubin'];need(re.search(rb'^\s*\.reqntid\s+1024(?:,\s*1,\s*1)?\s*$', fs[prefix+'exchange.ptx'],re.M) is not None,'Actual CTA size differs')
 text_sections.append(hashlib.sha256(section(cubin,'.text.exchange')).hexdigest())
 for i,c in enumerate(calls):
  need(c['state']==[(i+1)*64]*2 and c['errors']==[0,0] and c['exact_math_input_tail_and_once_passed'],'Math/once check')
  need(c['binary_sha256']==hashlib.sha256(cubin).hexdigest(),'Changed binary during trial')
  samples=c['ticks'];need(len(samples)==64 and len(c['smids'])==64,'Missing raw exchanges')
  for values,ids in zip(samples,c['smids']):
   aa,bb,cc,dd=values;need(0<aa<dd<2**63 and 0<bb<=cc<2**63,'Local raw order/width')
   need(ids[0]==ids[3] and ids[1]==ids[2] and ids[0]!=ids[1],'Different SMID scope')
  lo=max(v[2]-v[3] for v in samples);hi=min(v[1]-v[0] for v in samples)
  need([lo,hi]==c['causal_offset_tick_interval'] and lo<=0<=hi,'Actual fixed-offset constraints')
  if version==3:
   for key,subset in [('training_offset_tick_interval',samples[:32]),('heldout_offset_tick_interval',samples[32:])]:
    low=max(v[2]-v[3] for v in subset);high=min(v[1]-v[0] for v in subset)
    need([low,high]==c[key] and low<=0<=high,'Train/heldout constraints')
  summary.append(dict(version=version,trial=i,offset_tick_interval=[lo,hi],observed_pairs=c['distinct_sm_pairs'],state=c['state']))
 obj=f'runs/clock-causal-object-v{version}/output/'
 need(j(f'runs/clock-causal-object-v{version}/terminal.json')['returncode']==0,'Final object inspection')
 proof=j(obj+'result.json');need(proof['cubin_sha256']==hashlib.sha256(cubin).hexdigest(),'Inspected another object')
 need(proof['tool_sha256']=='6df0054fac801e7ab7d251506cfe52a1171c207de0923d8a3d57fdd5a1f6d982','Changed tool')
 need(len(proof['commands'])==4 and all(v['state']=='terminal' and v['returncode']==0 for v in proof['commands']),'Actual SASS/JSON/CFG failed')
 need(all('--no-dataflow' not in v['argv'] for v in proof['commands']) and b'digraph' in fs[obj+'cfg.stdout'],'CFG weakened')
 meta,functions=j(obj+'json.stdout');need(meta['SM']['version']==dict(major=12,minor=0),'Wrong actual target')
 need(len(functions)==1 and len(functions[0]['sass-instructions'])==280,'Changed final instruction count')
 getters=[(i*16,r) for i,r in enumerate(functions[0]['sass-instructions']) if 'GLOBALTIMER' in r.get('operands','')]
 need(len(getters)==4 and all(r['opcode']=='CS2R' and 'SR_GLOBALTIMERLO' in r['operands'] for _,r in getters),'Wrong actual clock getter')
 ptx=fs[prefix+'exchange.ptx'].decode().splitlines();raw_sources=section(cubin,'.nv_debug_ptx_txt').decode().split('\0')[:-1]
 text=fs[obj+'lines.stdout'].decode().splitlines();line=None;mapped={}
 for l in text:
  loc=re.match(r'\s*//## File "\.nv_debug_ptx_txt", line (\d+)',l)
  if loc:line=int(loc[1])
  instr=re.match(r'\s*/\*([0-9a-f]+)\*/\s*(.*?)\s*;',l)
  if instr and 'SR_GLOBALTIMERLO' in instr[2]:mapped[int(instr[1],16)]=line
 need(set(mapped)=={pc for pc,_ in getters},'Text/JSON getter set')
 for pc,ins in getters:
  n=mapped[pc]-1
  need('%globaltimer' in ptx[n] and re.sub(r'\s+','',ptx[n])==re.sub(r'\s+','',raw_sources[n]),'Exact getter PTX line')
  regname=re.search(r'mov.u64\s+(%\w+),',ptx[n])[1]
  publishes=[(i+1,l.strip()) for i,l in enumerate(ptx) if 'release.exch.b64' in l and re.search(re.escape(regname)+r'\s*;',l)]
  static.append(dict(version=version,pc=pc,ptx_line=n+1,ptx_result_register=regname,release_publications=publishes))
need(all(sum(bool(x['release_publications']) for x in static if x['version']==v)==2 for v in [2,3]),'Missing release value dependency')
need(text_sections[0]==text_sections[1],'Calibration GPU text changed during CPU caller integration')
for n in j('owned-terminal-status.json')['jobs']:
 need(all(w['state'] in ['missing','Z','pid_reused'] for w in n['owned']),'Live owned job')
result=dict(status='causal_constraints_and_exact_objects_audited_not_clock_certificate',source_freeze='880706b2cee327e71100b8fb99222666523d121d',actual_math_launches=6,actual_math_launches_final_version=3,exchanges_final_version=192,train_and_heldout_each_trial=32,common_clock_cpu_methods_each_mode=9,existing_clock_arithmetic_each_mode=27,trial_constraints=summary,actual_counter_sites=static,same_gpu_text_across_caller_integration=True,archive_bytes=a.archive.stat().st_size,archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),limits=['Observed CUDA SMID pair only, not all physical SM/epoch coverage','Causal bounds use ticks; scale/endpoint/quantization qualification remains separate','Actual clock reads and release inputs verified; full consumer control/epoch evidence remains to integrate','Dedicated calibration is not ordinary timeline/Perfetto/independent qualification'])
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
