"""Offline original-buffer and portable-compilation evidence audit, no tool imports."""
import base64
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
import statistics
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE / 'root-extracted'
def digest_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return digest_bytes(p.read_bytes())
counts = collections.Counter()
summary = []
llvm_pairs = {}
wait_rows = []
for rp in sorted(BASE.glob('round2-*/result.json')):
    result = json.loads(rp.read_text())
    assert result['status'] == 'passed_math_and_native'
    bundle = rp.parent / 'capture'
    for name, item in json.loads((bundle / 'manifest.json').read_text())['files'].items():
        path = Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        q = bundle / path
        assert q.is_file() and q.stat().st_size == item['bytes'] and sha(q) == item['sha256'], str(q)
        counts['bundle_manifest_entries'] += 1
    data = json.loads((bundle / 'ai/observations.json').read_text())
    by_capture = collections.defaultdict(dict)
    for e in data['observations']:
        assert e['association_status'] == 'verified'
        assert e['program_selection_status'] == 'consistent_with_expected_program' and e['expected_program'] == e['program'] == 0
        assert e['clock']['alignment'] == 'instance_local' and e['clock']['tick_ns'] == 20
        assert e['relative_start_ns'] is None
        index = int(e['id'].rsplit(':record', 1)[1])
        key = (e['actor_slot'], index)
        assert key not in by_capture[e['capture_id']]
        by_capture[e['capture_id']][key] = e
    for capture in data['captures']:
        assert capture['capture_status'] == 'decoded' and not capture['dropped'] and not capture['counter_saturated']
        raw = base64.b64decode(capture['raw_base64'], validate=True)
        assert digest_bytes(raw) == capture['raw_sha256']
        words = struct.unpack('<' + 'Q' * (len(raw) // 8), raw)
        cap = result['plan']['capacity']
        assert len(words) == 3 * (4 + cap * 8)
        found = 0
        for actor in range(3):
            offset = actor * (4 + cap * 8)
            version, cursor, attempted, dropped = words[offset:offset+4]
            assert version in (0, 1) and attempted == cursor + dropped and dropped == 0
            assert cursor <= cap
            if version == 0: assert cursor == attempted == 0
            prior = -1
            for index in range(cursor):
                record = list(words[offset+4+index*8:offset+4+(index+1)*8])
                desc, occurrence, start, end, program, recorded_actor, buffer, iteration = record
                assert program == 0 and recorded_actor == actor and prior < occurrence < attempted and end >= start
                prior = occurrence
                e = by_capture[capture['capture_id']][actor, index]
                assert record == e['original_record']
                assert (desc & 0xffffffff) == e['site'] and occurrence == e['occurrence']
                assert {1:'issue',2:'wait_bracket',3:'control_checkpoint'}[desc >> 32] == e['semantic']
                assert start == e['start_tick'] and end == e['end_tick']
                assert e['duration_ticks'] == end-start and e['duration_ns'] == 20*(end-start)
                if desc >> 32 == 3: assert start == end
                found += 1
        assert found == len(by_capture[capture['capture_id']])
        counts['raw_buffers'] += 1; counts['records'] += found
    assert len(data['observations']) == result['dynamic_observation_count']
    binaries = json.loads((bundle / 'ai/binaries.json').read_text())
    for binary in binaries:
        h = binary['compiler_metadata']['flagprism_ascend_handoff']
        assert h['phase'] == 'finished' and h['returncode'] == 0
        source = h['source_snapshot']
        raw = source['ir'].encode('utf-8')
        assert source['encoding'] == 'utf-8' and digest_bytes(raw) == source['ir_sha256']
        receipt = h['sdk_ir_capture']['receipt']
        assert receipt['compile_id'] == h['compile_id'] and receipt['source_ir_sha256'] == digest_bytes(raw)
        assert receipt['state'] == 'finished' and receipt['returncode'] == 0
        assert digest_bytes(h['sdk_ir_capture']['stderr'].encode()) == receipt['streams']['stderr']['sha256']
        originals = list(BASE.glob(f"**/{h['compile_id']}/source.mlir"))
        assert originals and all(q.read_bytes() == raw for q in originals)
        for a in h['artifacts']:
            assert digest_bytes(a['llir'].encode()) == a['sha256'] == a['metadata']['module_sha256']
            assert a['metadata']['compile_id'] == a['driver_job']['compile_id'] == h['compile_id']
            assert a['driver_job']['state'] == 'finished' and a['driver_job']['exit_code'] == 0
            assert digest_bytes(a['adapted']['llir'].encode()) == a['adapted']['sha256']
        ready = binary['execution_manifest']['mapping']['static_readiness']
        assert ready['source_binding'] == 'verified_durable_bytes_and_enclosing_compile'
        assert ready['compile_id'] == h['compile_id'] and ready['source_ir_sha256'] == digest_bytes(raw)
        assert ready['state'] == 'compiler_static' and len(ready['channels']) == 1
        channel, = ready['channels']
        assert channel['producer_actor_kind'] == 'AIC' and channel['consumer_actor_kind'] == 'AIV'
        assert channel['producer_pipeline'] == 'PIPE_FIX' and channel['consumer_pipeline'] == 'PIPE_S' and channel['flag_id'] == 0
        assert channel['dynamic_pairing'] == 'not_established'
        counts['portable_binary_source_bindings'] += 1
    measured = {s['invocation_identity']['invocation_id'] for s in result['samples']}
    assert len(measured) == result['plan']['samples']
    groups = collections.defaultdict(list)
    for e in data['observations']:
        if e['invocation_id'] in measured:
            groups[(e['invocation_id'],e['actor_slot'],e['site'],e['semantic'])].append(e)
    if 'fidelity_label' in result['plan']:
        allsite = result['plan']['fidelity_label'].endswith(':allsite')
        n = 4096 // result['config']['BK']
        label, mode = result['plan']['fidelity_label'].split(':')
        code = []
        for a in result['compiler_metadata']['flagprism_ascend_handoff']['artifacts']:
            text = '\n'.join(line for line in a['llir'].splitlines() if not line.startswith('; ModuleID ='))
            code.append((a['actor_kinds'], digest_bytes(text.encode())))
            if 'AIC' in a['actor_kinds']:
                assert re.search(r'%46 = phi i32 \[ %119, %117 \], \[ 0, %11 \]', text)
                assert f'%47 = icmp slt i32 %46, {n}' in text
                assert '%119 = add i32 %46, 1' in text
        llvm_pairs.setdefault(label, {})[mode] = sorted(code)
        for e in data['observations']:
            if e['invocation_id'] in measured and e['actor_slot'] in (1,2) and e['site'] == 0:
                wait_rows.append({'configuration':label,'mode':mode,'invocation_id':e['invocation_id'],'actor_slot':e['actor_slot'],'start_tick':e['start_tick'],'end_tick':e['end_tick'],'local_duration_us':e['duration_ns']/1000,'association_status':e['association_status']})
        for invocation in measured:
            for actor in (1,2): assert len(groups[invocation,actor,0,'wait_bracket']) == 1
            if allsite:
                for site in (6,9): assert len(groups[invocation,0,site,'issue']) == n
                assert len(groups[invocation,0,17,'control_checkpoint']) == n+1
            else: assert not any(e['semantic'] != 'wait_bracket' for e in data['observations'] if e['invocation_id']==invocation)
    medians = {}
    for actor in (1,2):
        values = [e['duration_ns']/1000 for e in data['observations'] if e['invocation_id'] in measured and e['actor_slot']==actor and e['site']==0]
        medians[str(actor)] = statistics.median(values)
    summary.append({'case': rp.parent.name, 'plan': result['plan'], 'measured_AIV_site0_median_us': medians, 'retained_records': len(data['observations']), 'result_sha256': sha(rp)})
    counts['results'] += 1
for modes in llvm_pairs.values(): assert modes['allsite'] == modes['wait-only']
with (HERE/'wait-fidelity-measured.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(wait_rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(wait_rows)
out = {'preinstrumentation_actor_LLVM_identical_after_ModuleID_path_removal': True, 'original_AIC_CFG_trip_count_independently_checked': True, 'status':'passed', 'scope':'independent offline original bytes, source binding, raw records and descriptive count/rate arithmetic; no fresh numerical execution or native wait accuracy certificate', 'counts':dict(counts), 'cases':summary, 'archive_sha256':sha(HERE/'round2-source-fidelity-evidence-r2.tgz')}
(HERE/'root-source-fidelity-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print('ROOT independent full audit passed',dict(counts))
for row in summary: print(row['case'],row['measured_AIV_site0_median_us'])
