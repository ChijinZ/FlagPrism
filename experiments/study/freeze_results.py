#!/usr/bin/env python3
"""Build a reviewable result bundle and audit every saved compiler artifact."""
import argparse,collections,csv,hashlib,json,shutil,statistics
from pathlib import Path
from observations import read,native
p=argparse.ArgumentParser();p.add_argument('--ascend',type=Path,required=True);p.add_argument('--enflame',type=Path,required=True);p.add_argument('--cuda',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
backends=[('cann',a.ascend,['full','native-full'] if (a.ascend/'native-full').exists() else ['full']),('enflame',a.enflame,['full'])]+([('cuda',a.cuda,['full'])] if a.cuda else [])
cases=[];samples=[];durations=[];audited=0
for backend,root,subdirs in backends:
 for sub in subdirs:
  for f in sorted((root/sub).glob('*/result.json')):
   d=read(f);case=f.parent
   identity={k:d.get(k) for k in ['backend','operator','variant','phase','device','status']};identity['shape']='x'.join(map(str,d['shape']));identity['raw_case']=str(case)
   cases.append({**identity,'validation_passed':d.get('validation',{}).get('passed'),'post_profile_validation_passed':d.get('post_profile_validation',{}).get('passed'),'target':d.get('runtime',{}).get('target'),'torch':d.get('runtime',{}).get('torch'),'triton':d.get('runtime',{}).get('triton'),'error':d.get('error')})
   if d['status']!='passed':continue
   assert d.get('validation',{}).get('passed'),f'Invalid correctness claim: {f}'
   for info in d.get('asm',{}).values():
    content=(case/info['file']).read_bytes();assert len(content)==info['bytes'];assert hashlib.sha256(content).hexdigest()==info['sha256'];audited+=1
   if d['phase']=='baseline':
    for i,sample in enumerate(d.get('samples',[])):samples.append({**identity,'sample_index':i,**sample})
   elif d['phase']=='native':
    assert d.get('post_profile_validation',{}).get('passed'),f'Profiled validation missing: {f}'
    ev=[e for e in native(case,backend) if e.get('kind')=='kernel' and e.get('duration_us') is not None]
    expected=d.get('profiling',{}).get('launch_count',3)
    assert len(ev)==expected,f'Expected {expected} observed device records: {case}, got {len(ev)}'
    for i,e in enumerate(ev):durations.append({**identity,'sample_index':i,'source':e.get('source'),'native_name':e.get('name'),'reported_duration_us':e['duration_us'],'scope':'vendor task interval' if backend=='cann' else 'device kernel interval'})
 if (root/'environment.json').exists():shutil.copy2(root/'environment.json',a.output/(backend+'-environment.json'))
def csvfile(name,rows):
 with (a.output/name).open('w') as f:
  w=csv.DictWriter(f,lineterminator='\n',fieldnames=list(dict.fromkeys(k for row in rows for k in row)));w.writeheader();w.writerows(rows)
csvfile('cases.csv',cases);csvfile('baseline_samples.csv',samples);csvfile('kernel_intervals.csv',durations)
summary={'cases':len(cases),'statuses':dict(collections.Counter(d['status'] for d in cases)),'baseline_batch_samples':len(samples),'native_intervals':len(durations),'compiler_artifacts_verified':audited,'backend_cases':dict(collections.Counter(d['backend'] for d in cases)),'limitations':['These are untuned study probes, not vendor-optimal implementations.','No exclusive-device or fixed-clock guarantee.','Native invocation samples share a process; min-max spans are not confidence intervals.','Canonical input hashes must be audited separately; seeds alone do not establish input identity.','Different compilers/SDKs: conclusions concern complete backend stacks.','Stream event intervals include host-fed gaps; do not substitute for kernel durations.','No independent internal pipeline timing or instance mismatch rate has been measured.']}
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
evidence=a.output/'evidence';evidence.mkdir(exist_ok=True)
lowering=a.ascend/('lowering-v2' if (a.ascend/'lowering-v2').exists() else 'lowering')
for name in (['gemm-128-debug','gemm-128-v1-debug','fused-128-debug'] if lowering.exists() else []):
 case=lowering/name;dump=next(case.rglob('kernel.npuir.mlir'));shutil.copy2(dump,evidence/(name+'.hivm.mlir'));shutil.copy2(case/'result.json',evidence/(name+'.result.json'))
for op in ['gemm','gemm_bias_gelu']:
 case=a.enflame/'full'/f'{op}-128x128x128-v0-baseline';shutil.copy2(case/'asm/gcuir',evidence/(op+'.gcu.mlir'))
 if not lowering.exists():continue
 cfg=[read(a.ascend/'full'/f'{op}-128x128x128-v0-baseline/result.json'),read(lowering/('gemm-128-debug' if op=='gemm' else 'fused-128-debug')/'result.json')]
 assert cfg[0]['asm']['npubin']['sha256']==cfg[1]['asm']['npubin']['sha256'],f'Compiler diagnostic changed baseline binary: {op}'
(a.output/'README.md').write_text('''# Hardware observations (bundle date in directory name)

`summary.json` records coverage and interpretation limits. `cases.csv` records
correctness and software versions. `kernel_intervals.csv` contains native
kernel/task durations (microseconds), the recorded number of prewarmed launches per case (15 in the new three-backend round).
`baseline_samples.csv` separately records host and stream-event intervals.
All saved compiler artifacts were checked against their per-case SHA-256.

Configurations: GEMM stages 1/2; row grouping 1/2; transpose M tile 16/32.
GEMM shapes: 128³, 512³, 257×193×320. Row shapes: 32×256, 256×1024,
127×769. Transpose shapes: 256², 1024², 513×257. GEMM input FP16, FP32
accumulation/output; other probes FP32. Canonical byte-identical inputs audited by analyze_deep.py; CPU PyTorch references.

`evidence/` holds actual emitted IR and diagnostic provenance. When diagnostic evidence is available, the script verifies Ascend
GEMM diagnostic binaries against corresponding baseline binary hashes.
When lowering evidence is present, its fused source becomes AIC and AIV functions with workspace/sync-block
coordination, while its native collector records one MIX_AIC task per launch.
This establishes decomposition/observation-scope differences, not internal
execution overlap or an attribution error.

GEMM stages 1/2: Ascend's emitted IR changes double buffering and event-ID
selection; Enflame and V100 corresponding final binary pairs are identical in this round
(see stage_binary_audit.json).
A configuration name alone does not establish an equivalent intervention.

Complete raw outputs, logs, binaries, profiler exports and archive snapshots
are retained under the project `artifacts/study-20261013/`. The raw-case column
locates these files in that workspace; generated HTML reports are not duplicated
in this compact Git bundle. Profiling capture itself changes execution.
Do not interpret these measurements as peak performance or submission-ready
cross-architecture causal evidence; see `summary.json` for outstanding limits.
''')
with (a.output/'README.md').open('a') as f:
 f.write('''

Additional evidence generated by analyze_deep.py and plot_deep.py:
- deep-audit.json and input_manifest.json: byte-identical input audit.
- nested_comparison.csv and region_probes/: median, ranges and individual samples.
- clock_calibration.csv and endpoint_ir_audit.json: valid endpoint-v2 controls.
- controlled_tile.csv: separate counter-free timings.
- tcu_invocations.csv/json: capture-local device/ID and per-SIP counter detail.
- raw_archives.json: full raw archive sizes/hashes (workspace archives, not Git binaries).
- figures/: final measured PDF/PNG figures; manuscript.pdf: local paper snapshot.
- reviews/: three independent reviews and the resulting revisions.

Separate single-region captures are references using the same vendor primitive,
not independent physical clocks. Generic nested subtraction is not a reproduction
of Proton/KPerfIR/TCU. Region probes measure instrumented brackets, not busy time.
TCU already supports the rich exported metrics; no vendor-tool incapability is claimed.
''')
print(json.dumps(summary))
