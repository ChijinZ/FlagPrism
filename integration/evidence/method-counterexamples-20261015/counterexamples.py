"""Offline, data-only counterexamples from immutable retained original captures."""
from pathlib import Path
import tarfile,json,hashlib,base64,struct
workspace=Path.cwd()
archive=workspace/'artifacts/method-run/enflame/cooperative4-vector-publication-before.tar.gz'
with tarfile.open(archive) as t:
 member=next(m for m in t if m.name.endswith('/ai/observations.json'))
 data=t.extractfile(member).read();j=json.loads(data);c=j['captures'][0];raw=base64.b64decode(c['raw_base64'],validate=True)
 assert hashlib.sha256(raw).hexdigest()==c['raw_sha256']
 header=struct.unpack('<8I',raw[:32]);assert header[0]==59 and header[4]==64
 records=[struct.unpack('<16I',raw[32+i*64:32+(i+1)*64]) for i in range(header[0])]
 assert all(all(w==0 for w in r[4:]) for r in records)
 log=t.extractfile('cooperative-tests.log').read().decode()
 assert 'assert all(e["start_tick"] > 0' in log and '1 failed' in log
 old={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'raw_sha256':c['raw_sha256'],'records':len(records),'first_record_16xu32':list(records[0]),'only_first_four_word_slice_published':True,'known_failure':'nonzero start_tick oracle failed; zero fields are missing publication, not measured zero latency','scope':'historical pre-repair capture; not a final-runtime failure'}
b=workspace/'artifacts/method-run/ascend/round2/origin-source-manifest-extracted/round2-origin-mix-r1/capture'
p=b/'ai/cann_native_tasks.json';native=json.loads(p.read_text());capture=native['capture'];assert capture['canonical_tasks']==4 and capture['dispatch_context_views']==4
new={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'canonical_compute_tasks':capture['canonical_tasks'],'retained_dispatch_context_views':capture['dispatch_context_views'],'source_associated_tasks':capture['associated_tasks'],'incorrect_if_all_eight_views_counted_as_compute':8,'scope':'offline counting counterexample from one retained four-launch capture, not another hardware experiment or measured legacy join'}
result={'publication':old,'context_views':new,'wait_sensitivity':'See original 120 per-call rows and paired modes in integration/evidence/ascend-wait-fidelity-20261015; mode-dependent medians are not local-error bounds.'}
output=workspace/'artifacts/method-review/round3/preparation/counterexamples.json';output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
