"""Actual original ELF byte checks and bounded end-to-record tail check."""
import argparse, hashlib, importlib.util, json, re, struct, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
inputs=Path(__file__).parent
spec=importlib.util.spec_from_file_location('values',inputs/'gcu_native_values.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for label,flags in [('normal',[]),('optimized',['-O'])]:
 with (a.output/(label+'.log')).open('xb') as log:
  cp=subprocess.run([sys.executable,'-I',*flags,'-m','pytest','-q',str(inputs/'Debugger/test/test_gcu_native_values.py'),'--basetemp',str(a.output/('pytest-'+label))],stdout=log,stderr=subprocess.STDOUT,timeout=30)
 if cp.returncode:raise ValueError('Native value-flow fixture failure: '+label)
r=Path('/tmp/chijin-timeline-r083-gcu/matching-loaded');binary=(r/'0.elf').read_bytes();native=(r/'0.native.stdout').read_bytes()
if hashlib.sha256(binary).hexdigest()!='7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500':raise ValueError('Original loaded ELF differs')
header=struct.unpack_from('<16sHHIQQQIHHHHHH',binary);sections=[struct.unpack_from('<IIQQQQIIQQ',binary,header[6]+i*header[11]) for i in range(header[12])];rows=[]
for line in native.decode().splitlines():
 m=re.match(r'^\s*([0-9a-f]+):\s+([^\t]+)\t(.+)$',line)
 if not m:continue
 pc=int(m[1],16)
 if not 0xabce<=pc<=0xb05a:continue
 raw=bytes.fromhex(m[2]);found=[s for s in sections if s[2]&4 and s[3]<=pc and pc+len(raw)<=s[3]+s[5]]
 if len(found)!=1:raise ValueError('Instruction outside unique executable section')
 s=found[0];offset=s[4]+pc-s[3]
 if binary[offset:offset+len(raw)]!=raw:raise ValueError('Displayed instruction bytes differ')
 asm=m[3].split(None,1);rows.append(dict(pc=pc,opcode=asm[0],operands=asm[1] if len(asm)>1 else ''))
answer=module.check_record_tail(rows,low_register='r13',high_register='r9',identity_register='r5')
answer.update(ELF_sha256=hashlib.sha256(binary).hexdigest(),native_sha256=hashlib.sha256(native).hexdigest(),helper_sha256=hashlib.sha256((inputs/'gcu_native_values.py').read_bytes()).hexdigest(),actual_tail_instruction_count=len(rows),actual_reader_inputs_independently_qualified=False,manual_actual_tail_selection=True,device_executed=False,application_replayed=False)
(a.output/'result.json').write_text(json.dumps(answer,indent=2))
