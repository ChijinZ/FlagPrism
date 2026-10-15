"""Read-only replay of binary-scoped inventory selection and effective output."""
from pathlib import Path
import json,hashlib
base=Path('artifacts/method-run/enflame/round2/root-extracted/i3-evidence/round2-softmax');rows=[]
for workers in (4,1):
 p=base/f'w{workers}'/'test_public_softmax_organizati0'
 m=json.loads((p/'compiled-metadata.json').read_text());d=json.loads((p/'diagnostic.json').read_text());b=p/'bundle'
 x=json.loads((b/'ai/execution.json').read_text())['binaries'][0]
 stores=[r['opId'] for r in m['debug_tracked_table'] if r['mlirOpName']=='tt.store']
 selected=d['request']['sites'];assert selected==[29] and selected[0] in stores
 o=json.loads((b/'ai/observations.json').read_text());assert len(o['observations'])==len(o['captures'])==1
 e=o['observations'][0];assert e['association_status']=='verified' and e['site']==selected[0] and e['program']==0 and e['duration_ns'] is None
 c=o['captures'][0];assert c['header']['overflow_count']==0 and not c['counter_saturated']
 assert d['math']['passed'] and d['math']['input_unchanged'] and d['math']['output_guards_unchanged']
 rows.append({'work_items':workers,'binary_id':x['binary_id'],'tracked_inventory_sha256':hashlib.sha256((p/'compiled-metadata.json').read_bytes()).hexdigest(),'available_store_sites':stores,'selected_site':29,'fresh_inventory_validates_actual_binary':True,'records':1,'dropped':0,'duration_unit':'unknown-frequency ticks','mapping_work_item_count':x['mapping']['work_item_count']})
assert rows[0]['binary_id']!=rows[1]['binary_id']
out={'scope':'offline replay of original current public captures, no new GPU/compilation or measured onboarding; each binary inventory checked separately even though numeric site ID stays29','rows':rows}
Path('artifacts/method-review/round3/preparation/workflow-replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
