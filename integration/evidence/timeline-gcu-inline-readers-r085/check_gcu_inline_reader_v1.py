"""Infer clock registers in unchanged loaded GCU objects; no replay/codegen."""
import argparse,hashlib,importlib.util,json,re,struct,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True);inputs=Path(__file__).parent
spec=importlib.util.spec_from_file_location('values',inputs/'gcu_native_values.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for label,flags in [('normal',[]),('optimized',['-O'])]:
 with (a.output/(label+'.log')).open('xb') as log:cp=subprocess.run([sys.executable,'-I',*flags,'-m','pytest','-q',str(inputs/'Debugger/test/test_gcu_native_values.py'),'--basetemp',str(a.output/('pytest-'+label))],stdout=log,stderr=subprocess.STDOUT,timeout=30)
 if cp.returncode:raise ValueError('Inline reader fixture failed: '+label)
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
 all_bodies.append(body);rows=[];seen=set()
 for location in record['locations']['locations']:
  if location['phase']!='end_counter' or location['address'] in seen:continue
  seen.add(location['address'])
  try:answer=module.inspect_inline_reader(body,marker_packet=location['address'])
  except ValueError as error:answer=dict(status='unverified',error=str(error))
  rows.append(dict(location=location,answer=answer))
 reports.append(dict(ELF_sha256=record['elf_sha256'],native_sha256=record['native_sha256'],readers=rows))
# The unchanged actual shared-end tail is an explicit structural regression case.
# Registers are now inferred from the actual marker's read/rollover data flow.
actual=module.inspect_inline_record_fields(all_bodies[0],marker_packet=0xaaa0,tail_start_pc=0xabce,tail_end_pc=0xb05a)
(a.output/'result.json').write_text(json.dumps(dict(status='inline_reader_shape_and_relative_record_fields_checked',reports=reports,actual_shared_end=actual,helper_sha256=hashlib.sha256((inputs/'gcu_native_values.py').read_bytes()).hexdigest(),manual_actual_tail_selection=True,automatic_MMIO_or_source_boundary_qualification=False,device_executed=False,application_replayed=False),indent=2))
