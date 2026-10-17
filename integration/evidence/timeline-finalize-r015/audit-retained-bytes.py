"""Stdlib/Git audit of retained actual captures; no product imports or execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive', required=True, type=Path)
p.add_argument('--repo', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()

def need(value, message):
    if not value:
        raise RuntimeError(message)

with tarfile.open(a.archive) as t:
    files = {m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}

def j(name):
    return json.loads(files[name])

freeze = 'f17071ccd6a7514507e583a71b27fe6030752ff9'
for path in ['hooks/timeline.py','timeline_runtime.py']:
    expected = subprocess.check_output(['git','-C',str(a.repo),'show',freeze+':Profiler/python/flagtree_profiler/'+path])
    need(files['installed/'+path] == expected, 'Installed source mismatch: '+path)
for name in ['test_timeline_runtime.py','test_timeline_finalize.py','test_public_timeline_contract.py',
             'p01_nvidia_finalize_recovery.py','ordinary_timeline_workload.py']:
    expected = subprocess.check_output(['git','-C',str(a.repo),'show',freeze+':tests/timeline/'+name])
    need(files['check-input-v2/'+name]==expected, 'Executed test source mismatch: '+name)
for name in ['package-finalize-v1','package-finalize-v2']:
    receipt = j(name+'/terminal.json')
    need(receipt['state']=='build_passed_not_device_qualified', 'Package terminal')
    bridge = j(name+'/native-byte-bridge.json')
    need(bridge['byte_equal'] and len(bridge['native_members'])==7, 'Native bytes changed')
need(j('package-finalize-v2/terminal.json')['component_commit']==freeze, 'Wrong product freeze')
need(j('runs/install-v2/output/result.json')['installed_members_byte_verified']==608, 'Installed wheel bytes')
need(j('runs/install-v2/output/result.json')['wheel_sha256']==j('package-finalize-v2/terminal.json')['wheel_sha256'], 'Wheel/install mismatch')
for mode in ['normal','optimized']:
    need(b'Ran 16 tests' in files[f'runs/install-v2/output/owner-contract-{mode}.stderr.log'] and
         b'\nOK\n' in files[f'runs/install-v2/output/owner-contract-{mode}.stderr.log'], 'Owner contracts')
    need(b'7 passed' in files[f'runs/install-v2/output/test_timeline_finalize.py-{mode}.stdout.log'], 'Finalization contracts')
    need(b'4 passed' in files[f'runs/install-v2/output/test_public_timeline_contract.py-{mode}.stdout.log'], 'Public contracts')
for name in ['fault-recovery-v1','fault-recovery-v2']:
    need(j('runs/'+name+'/terminal.json')['returncode']==1, 'First failure was lost')
need(b'FileNotFoundError' in files['runs/fault-recovery-v1/stderr.log'], 'First harness path failure')
need(any(b'slots must be a nonempty tuple' in b for n,b in files.items()
         if n.startswith('runs/fault-recovery-v2/') and n.endswith('/index.json')), 'Actual tuple rehydration failure')
terminal = j('runs/fault-recovery-v3/terminal.json')
need(terminal['returncode']==0, 'Final actual device run failed')
result = j('runs/fault-recovery-v3/output/result.json')
need(result['status']=='actual_owner_salvage_and_offline_retry_passed_not_full_P01', 'Wrong result')
need(result['recovery_transport_actions']==0 and result['explicit_workload_runs']==2, 'Recovery replay/transport work')
need(len(result['transport_actions'])==8 and
     [x['action'] for x in result['transport_actions']].count('read_raw')==4 and
     [x['action'] for x in result['transport_actions']].count('release')==4, 'Real transport actions')
need(not result['clock_qualified'] and not result['region_boundaries_verified'] and not result['perfetto_qualified'], 'False qualification')
root_prefix = '/workspace/chijin-timeline-r015/'
original = result['original_directory'].removeprefix(root_prefix)+'/'
first = j(original+'attempts/flush-0001.json')
second = j(original+'attempts/flush-0002.json')
need(not first['retained_owners'] and len(first['failures'])==1 and
     first['pending_decode']==[result['injected_invocation']], 'First failure owner/salvage state')
need(not second['failures'] and not second['retained_owners'] and not second['pending_decode'], 'Recovery pending state')
need(hashlib.sha256(files[original+'attempts/flush-0001.json']).hexdigest()==result['first_attempt_sha256'], 'First failure history changed')
for name,sha in result['originals'].items():
    need(hashlib.sha256(files[original+name]).hexdigest()==sha, 'Recovery rewrote original')
seen = set()
record_count = event_count = 0
for prefix in [original, 'runs/fault-recovery-v3/output/after-fault/timeline/']:
    index = j(prefix+'index.json')
    need(len(index['captures'])==4 and not index['failures'] and not index['pending_decode'] and
         not index['retained_owners'] and index['status']=='partial_clock_unverified', 'Final index')
    for row in index['captures']:
        capture = j(prefix+row['capture_file'])
        owner = capture['owner']
        identity = owner['invocation_id']
        need(identity not in seen and owner['state']=='raw_ready' and owner['submission_outcome']=='returned', 'Owner identity/completion')
        seen.add(identity)
        need(capture['capture_status']=='raw_complete', 'Capture incomplete')
        raw = files[prefix+capture['raw_file']]
        need(hashlib.sha256(raw).hexdigest()==capture['raw_sha256'], 'Raw SHA')
        original_input = j(prefix+str(Path(capture['raw_file']).with_suffix('.input.json')))
        need(original_input['owner']==owner and original_input['metadata']==capture['metadata'] and
             original_input['capture_status']=='raw_persisted_pending_decode', 'Durable input snapshot')
        decoded = j(prefix+capture['decoded_file'])
        canonical = j(prefix+capture['events_file'])
        need(canonical['complete'] and canonical['clock_status']=='unverified' and
             canonical['boundary_status']=='unverified' and
             canonical['identity']['invocation_id']==identity, 'Canonical qualification/identity')
        need(len(decoded['records'])==len(canonical['records']), 'Lost raw records')
        decoded_map = {}
        for record in decoded['records']:
            offset = record['raw_byte_offset']
            tag,lo,hi,seq = struct.unpack_from('<4I',raw,offset)
            need(record['raw_byte_length']==16 and seq==record['sequence'] and
                 record['site']==tag&0x7fffffff and record['tick']==lo+(hi<<32) and
                 record['phase']==('exit' if tag&0x80000000 else 'entry'), 'Physical endpoint mismatch')
            decoded_map[offset] = record
        refs = {}
        for record in canonical['records']:
            native = decoded_map[record['offset']]
            need(record['length']==16 and record['tick']==native['tick'] and
                 record['sequence']==native['sequence'] and record['phase']==native['phase'], 'Canonical raw reference')
            refs[record['id']] = record
        for event in canonical['events']:
            begin,end = [refs[r] for r in event['record_ids']]
            need(event['kind']=='interval' and begin['phase']=='entry' and end['phase']=='exit' and
                 begin['observer_id']==end['observer_id']==event['observer_id'] and
                 begin['site_id']==end['site_id']==event['site_id'] and
                 begin['tick']==event['start_tick'] and end['tick']==event['end_tick'], 'Pair changed during recovery')
        need(capture['machine_counter_mapping']['status']=='counter_mapping_complete_region_unverified', 'Machine status')
        record_count += len(canonical['records'])
        event_count += len(canonical['events'])
for name in ['fault-math','after-fault-math']:
    prefix='runs/fault-recovery-v3/output/'+name+'/'
    need(b'passed' in files[prefix+'math-passed.txt'] and b'one explicit' in files[prefix+'host-once.txt'], 'Actual math/input/tail/side effect result')
need(len(seen)==8 and event_count==1344 and record_count==2688, 'Actual capture totals')
for job in j('owned-final.json'):
    for owner in job['owners']:
        need(not owner['same_startticks'] or owner['current_state']=='Z', 'Live owned process')
output = dict(status='installed_owner_salvage_and_actual_raw_pairs_audited_not_full_P01',
    product_freeze=freeze, archive_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
    archive_bytes=a.archive.stat().st_size, archive_members=len(files), installed_members=608,
    captures=len(seen), raw_endpoint_references=record_count, intervals=event_count,
    recovery_transport_actions=0, normal_and_optimized_contracts={'owner':16,'finalization':7,'public':4},
    first_harness_failure_preserved=True, first_product_failure_preserved=True,
    clock_qualified=False, region_boundaries_verified=False, perfetto_qualified=False)
a.output.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output))
