"""Check real Perfetto slices against retained canonical observer events."""
import argparse,csv,io,json,subprocess,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--processor',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[]
for trace in sorted(a.directory.rglob('*.counter-ticks.pftrace')):
 m=re.fullmatch(r'(.*)\.observer-(\d+)\.counter-ticks\.pftrace',trace.name)
 canonical=trace.with_name(m[1]+'.events.json');d=json.loads(canonical.read_text());assert d['complete'],str(canonical)
 observer=d['observers'][int(m[2])];expected=sum(e['observer_id']==observer['id'] for e in d['events'])
 sql="SELECT count(*) AS slices, coalesce(sum(dur < 0),0) AS unfinished, (SELECT count(*) FROM track WHERE name LIKE '%NOT ns%') AS tick_labels FROM slice;"
 r=subprocess.run([a.processor,'query','--format','csv',str(trace),sql],capture_output=True,text=True,timeout=45)
 if r.returncode:raise RuntimeError(r.stderr)
 row=next(csv.DictReader(io.StringIO(r.stdout)))
 assert int(row['slices'])==expected,(trace,row,expected)
 assert int(row['unfinished'])==0 and int(row['tick_labels'])>=1,(trace,row)
 rows.append({'file':str(trace),'expected_events':expected,'observed_slices':int(row['slices']),'unfinished':0,'explicit_tick_track_labels':int(row['tick_labels']),'canonical_complete':True})
assert rows,'No traces found'
version=subprocess.run([a.processor,'--version'],capture_output=True,text=True,check=True).stdout.strip()
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'processor':version,'checks':rows},indent=2));print(str(len(rows))+' actual traces parsed, all slices match canonical events')
