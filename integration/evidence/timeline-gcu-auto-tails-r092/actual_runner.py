"""Automatic reader/record block checks against two unchanged loaded objects."""
import argparse, hashlib, importlib.util, json, re, struct, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inputs=Path(__file__).parent

import ast
files=['Debugger/python/flagtree_debugger/gcu_native_values.py','Debugger/test/test_gcu_native_values.py']
before={n:ast.dump(ast.parse((inputs/n).read_bytes())) for n in files}
subprocess.run(['git','init','-q'],cwd=inputs,check=True,timeout=10)
steps=[]
for iteration in range(2):
 for hook in ['ruff','yapf','check-ast']:
  cp=subprocess.run(['/tmp/chijin-usability-r6-recipe-tests/format-venv/bin/pre-commit','run',hook,'--files',*files],cwd=inputs,capture_output=True,timeout=35)
  steps.append(dict(iteration=iteration,hook=hook,returncode=cp.returncode,stdout=cp.stdout.decode(),stderr=cp.stderr.decode()))
  (a.output/'format.json').write_text(json.dumps(steps,indent=2))
  if iteration==1 and cp.returncode:raise RuntimeError('Formatting incomplete')
for n in files:
 if ast.dump(ast.parse((inputs/n).read_bytes()))!=before[n]:raise ValueError('Formatter changed AST')

helper=inputs/'Debugger/python/flagtree_debugger/gcu_native_values.py'
spec=importlib.util.spec_from_file_location('values',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for label,flags in [('normal',[]),('optimized',['-O'])]:
 with (a.output/(label+'.log')).open('xb') as log:
  cp=subprocess.run([sys.executable,'-I',*flags,'-m','pytest','-q',str(inputs/'Debugger/test/test_gcu_native_values.py'),'--basetemp',str(a.output/('pytest-'+label))],stdout=log,stderr=subprocess.STDOUT,timeout=30)
 if cp.returncode:raise ValueError('Automatic tail semantic fixture failed: '+label)
r=Path('/tmp/chijin-timeline-r083-gcu/matching-loaded');registered=json.loads((r/'result.json').read_text());reports=[];all_bodies=[]
for record in registered:
 binary=Path(record['elf']).read_bytes();native=Path(record['native_file']).read_bytes()
 for payload,key in [(binary,'elf_sha256'),(native,'native_sha256')]:
  if hashlib.sha256(payload).hexdigest()!=record[key]:raise ValueError('Original loaded object differs')
 header=struct.unpack_from('<16sHHIQQQIHHHHHH',binary);sections=[struct.unpack_from('<IIQQQQIIQQ',binary,header[6]+i*header[11]) for i in range(header[12])];body=[]
 for line in native.decode().splitlines():
  m=re.match(r'^\s*([0-9a-f]+):\s+([^\t]+)\t(.+)$',line)
  if not m:continue
  pc=int(m[1],16);raw=bytes.fromhex(m[2]);found=[s for s in sections if s[2]&4 and s[3]<=pc and pc+len(raw)<=s[3]+s[5]]
  if len(found)!=1:raise ValueError('Native instruction outside unique executable section')
  s=found[0];offset=s[4]+pc-s[3]
  if binary[offset:offset+len(raw)]!=raw:raise ValueError('Native instruction bytes differ')
  asm=m[3].split(None,1);body.append(dict(pc=pc,opcode=asm[0],operands=asm[1] if len(asm)>1 else ''))
 executable=[s for s in sections if s[2]&4 and s[5]]
 if len(executable)!=1:raise ValueError('Expected retained single executable extent')
 e=executable[0]
 # LLVM11 zero-suppression must not hide any nonzero executable bytes.
 coverage=bytearray(e[5])
 for line in native.decode().splitlines():
  m=re.match(r'^\s*([0-9a-f]+):\s+([^\t]+)\t(.+)$',line)
  if m:
   start=int(m[1],16)-e[3];n=len(bytes.fromhex(m[2]));coverage[start:start+n]=bytes([1])*n
 # This target stores a vendor kernel descriptor in .text, before code.
 descriptors=list(re.finditer(r'^([0-9a-f]{16}) ([^\n]+):\n\t\.dtu_kernel_code_t\n(.*?)\t\.end_dtu_kernel_code_t',native.decode(),re.M|re.S))
 if len(descriptors)!=1:raise ValueError('Expected one original kernel descriptor')
 descriptor=descriptors[0];base=int(descriptor[1],16);name=descriptor[2]
 entry=int(re.search(r'kernel_code_entry_byte_offset (\d+)',descriptor[3])[1]);size=int(re.search(r'kernel_code_size (\d+)',descriptor[3])[1]);symbols=[]
 for section in sections:
  if section[1]!=2:continue
  strings_section=sections[section[6]];strings=binary[strings_section[4]:strings_section[4]+strings_section[5]]
  for offset in range(section[4],section[4]+section[5],section[9]):
   sn,info,other,ix,value,extent=struct.unpack_from('<IBBHQQ',binary,offset);symbol=strings[sn:].split(b'\0',1)[0].decode()
   if symbol==name:symbols.append((value,extent,ix))
 if len(symbols)!=1 or symbols[0][:2]!=(base,entry+size) or not (e[3]<=base<base+entry<base+entry+size<=e[3]+e[5]) or entry%16 or size%16:raise ValueError('Descriptor/code range differs from original ELF symbol')
 coverage[base-e[3]:base+entry-e[3]]=bytes([1])*entry
 if any(v and not seen for v,seen in zip(binary[e[4]:e[4]+e[5]],coverage)):raise ValueError('Unaccounted nonzero bytes outside kernel metadata')
 body=[row for row in body if base+entry<=row['pc']<base+entry+size]
 rows=[];seen=set()
 for location in record['locations']['locations']:
  if location['phase']!='end_counter' or location['address'] in seen:continue
  seen.add(location['address'])
  try:answer=module.inspect_inline_record_fields_auto(body,marker_packet=location['address'])
  except ValueError as error:answer=dict(status='unverified',error=str(error))
  rows.append(dict(location=location,answer=answer))
 reports.append(dict(ELF_sha256=record['elf_sha256'],native_sha256=record['native_sha256'],automatic_record_blocks=rows))
(a.output/'result.json').write_text(json.dumps(dict(status='automatic_relative_record_blocks_inspected',reports=reports,helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),manual_actual_tail_selection=False,source_loop_qualified=False,default_capture_integrated=False,device_executed=False,SDK_recompiled=False,application_replayed=False),indent=2))
