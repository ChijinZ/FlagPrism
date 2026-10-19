from pathlib import Path
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
installed=Path('/workspace/chijin-timeline-r070-nvidia/runs/native-install-v3/output');timeline=installed/'public-timeline';public=json.loads((installed/'installed-public-reexport.log').read_text());cap=public['captures'][0];original=json.loads((timeline/('captures/'+cap['invocation_id']+'.input.json')).read_text());rows=[]
for old in cap['observed_dependency_exports']:
 row=dict(old);row['raw_file']=original['raw_file'];row['inputs_file']=str(Path(row['receipt_file']).parent/'inputs.json')
 for key in ['trace_file','view_file','raw_file','receipt_file','inputs_file']:row[key]=str(timeline/row[key])
 rows.append(row)
if len(rows)!=2:raise RuntimeError('Expected exact2 newly qualified actual exports')
manifest=a.output/'manifest.json';manifest.write_text(json.dumps(rows,indent=2));verifier=Path('/workspace/chijin-timeline-r059-nvidia/tools-smoke-input-v1/source/verify_dependency_traces.py')
if hashlib.sha256(verifier.read_bytes()).hexdigest()!='0d72cf3a882ea4b9d3bd1fe6c7172066fa486f708db8d2787ae47aef15147e03':raise RuntimeError('Verifier changed')
with (a.output/'stdout.log').open('xb') as out,(a.output/'stderr.log').open('xb') as err:
 subprocess.run([sys.executable,'-I',str(verifier),'--manifest',str(manifest),'--output',str(a.output/'verified')],stdout=out,stderr=err,check=True,timeout=70)
