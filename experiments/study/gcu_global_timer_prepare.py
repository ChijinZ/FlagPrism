#!/usr/bin/env python3
"""Derive a bounded read-only device shim from the installed SDK, with receipts."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--library',type=Path,default=Path('/opt/tops/llvm11/lib/krt/gcu300_api_profile.bc'));p.add_argument('--opt',default='/opt/tops/llvm11/bin/opt');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
with tempfile.TemporaryDirectory(prefix='study-sdk-timer-') as t:
 ll=Path(t)/'sdk.ll';q=subprocess.run([a.opt,'-S',str(a.library),'-o',str(ll)],capture_output=True,timeout=60);(a.output/'sdk-extract.log').write_bytes(q.stdout+q.stderr);q.check_returncode();text=ll.read_text()
 m=re.search(r'define dso_local i64 @_ZN4tops12global_timerEv\(\) local_unnamed_addr #\d+ \{[\s\S]*?\n\}',text);assert m,'SDK helper signature not recognized'
 fn=m[0];assert 'store ' not in fn and 'call ' not in fn and 'load volatile' in fn,'Read-only helper invariant failed'
 body=re.sub(r', !tbaa !\d+','',fn);body=re.sub(r'define dso_local i64 @_ZN4tops12global_timerEv\(\) local_unnamed_addr #\d+','define weak i64 @study_sdk_global_timer() alwaysinline nounwind',body)
 header='\n'.join(line for line in text.splitlines() if line.startswith(('target datalayout =','target triple =')))
 shim=a.output/'global-timer-shim.ll';shim.write_text(header+'\n'+body+'\n')
 summaries={}
 for symbol in ['_ZN4tops15krt_clock_startEv','_ZN4tops14krt_clock_stopEv','_ZN4tops9krt_clockEv','_ZN4tops12global_timerEv']:
  f=re.search(r'define[^\n]*@'+symbol+r'\([^\n]*\)[^\n]*\{[\s\S]*?\n\}',text)
  if f:summaries[symbol]={'sha256':hashlib.sha256(f[0].encode()).hexdigest(),'lines':len(f[0].splitlines()),'volatile_loads':f[0].count('load volatile'),'volatile_stores':f[0].count('store volatile')}
 receipt={'sdk_bitcode':str(a.library),'sdk_sha256':hashlib.sha256(a.library.read_bytes()).hexdigest(),'original_function_sha256':hashlib.sha256(fn.encode()).hexdigest(),'shim_sha256':hashlib.sha256(shim.read_bytes()).hexdigest(),'transformation':'Only rename/linkage/inline annotation and TBAA removal; original SDK volatile read/rollover/mask instructions retained. No invented MMIO addresses or MMIO writes.','sdk_function_fingerprints':summaries,'sdk_source_bulk_not_retained':True}
 (a.output/'provenance.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
