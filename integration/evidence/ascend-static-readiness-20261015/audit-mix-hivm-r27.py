from pathlib import Path
import json,hashlib,base64,collections,re
root=Path('artifacts/method-run/ascend/mix-hivm-lineinfo-r27-evidence-extracted')
bundle=root/'mix-lineinfo-r2/capture';manifest=json.loads((bundle/'manifest.json').read_text())
for name,meta in manifest['files'].items():
 p=(bundle/name).resolve();assert p.is_relative_to(bundle.resolve());raw=p.read_bytes();assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256']
binary,=json.loads((bundle/'ai/binaries.json').read_text());mapping=binary['execution_manifest']['mapping'];handoff=binary['compiler_metadata']['flagprism_ascend_handoff'];capture=handoff['sdk_ir_capture'];receipt=capture['receipt'];stream=capture['stderr']
assert receipt['state']=='finished' and receipt['returncode']==0
assert receipt['compile_id']==handoff['compile_id']
assert hashlib.sha256(stream.encode()).hexdigest()==receipt['streams']['stderr']['sha256']
assert receipt['streams']['stderr']['truncated'] is False
sourcefile=root/'mix-lineinfo-compiler-captures-r2'/receipt['compile_id']/'source.mlir'
assert hashlib.sha256(sourcefile.read_bytes()).hexdigest()==receipt['source_ir_sha256']==handoff['source_snapshot']['ir_sha256']
assert '--enable-debug-info=true' in receipt['command']
artifacts=handoff['artifacts'];assert len(artifacts)==2
origins=0
for artifact in artifacts:
 assert hashlib.sha256(artifact['llir'].encode()).hexdigest()==artifact['sha256']==artifact['metadata']['module_sha256']
 assert artifact['driver_job']['compile_id']==receipt['compile_id']
 for site in artifact['metadata']['dynamic_sites']:
  origins+=bool(site.get('debug_file') and site.get('debug_line'))
static=mapping['static_readiness'];channel,=static['channels'];assert static['state']=='compiler_static';assert static['clock_alignment']=='not_established';assert channel['producer_actor_kind']=='AIC' and channel['consumer_actor_kind']=='AIV'
actorids={a['id'] for a in mapping['actors']}
assert channel['producer_actor_id'] in actorids and channel['consumer_actor_id'] in actorids
assert channel['dynamic_generation'] is None and channel['dynamic_pairing']=='not_established'
setsite,waitsite=static['sites'];assert 'sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 0' in stream and 'sync_block_wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 0' in stream
for site in static['sites']:
 assert stream.splitlines()[site['dump_line']-1].strip()==site['raw_ir']
 assert site['state']=='verified_same_compile_actor'
obs=json.loads((bundle/'ai/observations.json').read_text());assert len(obs['observations'])==232 and len(obs['captures'])==4
actors=collections.Counter()
for event in obs['observations']:
 actors[str(event['actor_slot'])]+=1
 assert event['association_status']=='verified' and event['clock']['alignment']=='instance_local'
 assert event['duration_ns']==((event['end_tick']-event['start_tick'])%(1<<64))*20
for c in obs['captures']:
 raw=base64.b64decode(c['raw_base64'],validate=True);assert hashlib.sha256(raw).hexdigest()==c['raw_sha256']
 assert c['capture_status']=='decoded' and not c['dropped'] and not c.get('counter_saturated')
assert dict(actors)=={'0':192,'1':20,'2':20}
quality=json.loads(Path('artifacts/method-run/ascend/hivm-r27-quality-r3-summary.json').read_text());checked=[]
for item in quality['files']:
 p=Path('FlagPrism-method')/item['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['after_sha256'];assert item['ast_equal'] and item['idempotent'] and not item['ruff_new_diagnostics'];checked.append(item['file'])
result={'status':'independent_retained_M1_capture_audit_passed','bundle_manifest_files':len(manifest['files']),'binary':binary['id'],'actual_compile_id':receipt['compile_id'],'source_ir_sha256':receipt['source_ir_sha256'],'sdk_ir_sha256':static['sdk_ir_sha256'],'static_channels':1,'dynamic_sites_with_debug_origins':origins,'events':232,'captures':4,'actor_counts':dict(actors),'quality_source_files':checked,'limits':['Source locations are origin candidates, not exclusive source costs.','Static readiness does not pair dynamic generations or verify clock origin.','This is offline audit of real Docker data, not a new hardware execution.']}
Path('artifacts/method-run/ascend/mix-hivm-root-independent-audit-r27.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
