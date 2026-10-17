"""Stdlib byte audit of retained originals; no product import or math replay."""
import argparse,base64,hashlib,json,struct,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[]
with tarfile.open(a.archive) as tar:
 def get(name):return tar.extractfile(name).read()
 for i in range(4):
  prefix=f'runs/producer-v3/output/capture-{i}'
  raw=get(prefix+'.raw');doc=json.loads(get(prefix+'.input.json'));batch=json.loads(get(prefix+'.events.json'))
  if base64.b64decode(doc['capture']['raw_base64'])!=raw:raise RuntimeError('Original/base64 mismatch')
  digest=hashlib.sha256(raw).hexdigest()
  if digest!=batch['raw_artifact']['sha256'] or len(raw)!=batch['raw_artifact']['bytes']:raise RuntimeError('Raw binding mismatch')
  metadata=doc['compiler_metadata'];runtime=doc['capture']['runtime_metadata'];grid=runtime['grid'];total=grid[0]*grid[1]*grid[2]
  programs=[0] if total==1 else [0,total-1];stride=metadata['debug_dynamic_slot_bytes']
  if len(raw)!=len(programs)*stride or stride%4:raise RuntimeError('Physical slot extent/units mismatch')
  by_id={r['id']:r for r in batch['records']};counts=[]
  for slot,program in enumerate(programs):
   base=slot*stride
   written,capacity,dropped,flags,record_stride,payload,attempted,reserved=struct.unpack_from('<8I',raw,base)
   if not flags&32 or reserved!=program or payload!=stride or record_stride!=64:raise RuntimeError('Writer/header mismatch')
   for ordinal in range(min(written,capacity)):
    fields=struct.unpack_from('<HHIQQQQIIQQ',raw,base+32+ordinal*64)
    if fields[0]!=7 or fields[3]!=program or fields[-1]!=0x465044594e563031:raise RuntimeError('Real commit/program mismatch')
   observer=batch['observers'][slot]
   count=sum(e['observer_id']==observer['id'] for e in batch['events'])
   if count<2:raise RuntimeError('Host coordinates without actual events')
   counts.append(count)
  for r in batch['records']:
   if r['length']!=8 or not 0<=r['offset']<=len(raw)-8 or struct.unpack_from('<Q',raw,r['offset'])[0]!=r['tick']:raise RuntimeError('Endpoint field mismatch')
  for e in batch['events']:
   refs=[by_id[r] for r in e['record_ids']]
   if [r['phase'] for r in refs]!=['entry','exit'] or [r['tick'] for r in refs]!=[e['start_tick'],e['end_tick']]:raise RuntimeError('Event/endpoints mismatch')
  rows.append(dict(capture=i,grid=grid,raw_bytes=len(raw),raw_sha256=digest,events_per_observer=counts,endpoints=len(batch['records']),complete=batch['complete'],dropped_endpoint_references=sum(o['dropped_records'] for o in batch['observers'])))
 result=json.loads(get('runs/default-export-v2/output/result.json'))
 if result['events']!=28 or result['canonical_records']!=56:raise RuntimeError('Standard advanced bridge result changed')
 for name in ['runs/install-v3/terminal.json','runs/install-v4/terminal.json','runs/producer-v3/terminal.json','runs/default-export-v2/terminal.json']:
  d=json.loads(get(name))
  if d['state']!='terminal' or d['returncode']!=0:raise RuntimeError('Nonterminal or failed accepted job '+name)
 if rows[:3] and [r['events_per_observer'] for r in rows[:3]]!=[[10,10],[14,14],[18]]:raise RuntimeError('Runtime occurrence count changed')
 if rows[3]['complete'] or rows[3]['dropped_endpoint_references']!=56:raise RuntimeError('Overflow was concealed')
 output=dict(status='original_raw_byte_audit_passed_not_clock_boundary_guard_or_P01',archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),archive_bytes=a.archive.stat().st_size,archive_members=len(tar.getmembers()),captures=rows,standard_advanced_export=result,limitations=['No product code imported or application replayed','No proof of machine source boundaries, clock scale/epoch, allocation guard or Perfetto'])
a.output.write_text(json.dumps(output,indent=2)+'\n')
