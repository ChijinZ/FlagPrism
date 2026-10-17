"""Stdlib retained-byte checks only; no product imports or math oracle execution."""
import argparse
import base64
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
import tarfile


def need(value, message):
    if not value:
        raise RuntimeError(message)


def load(path):
    with tarfile.open(path) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo', type=Path, required=True)
p.add_argument('--nvidia-v1', type=Path, required=True)
p.add_argument('--nvidia-v2', type=Path, required=True)
p.add_argument('--enflame', type=Path, required=True)
p.add_argument('--prior-nvidia', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
old, new, gcu = load(a.nvidia_v1), load(a.nvidia_v2), load(a.enflame)
prior = load(a.prior_nvidia)
actual_objects = {}
for name in prior:
    if name.endswith('/counter-map.json'):
        proof = json.loads(prior[name]); prefix = name.rsplit('/', 1)[0]
        actual_objects[proof['artifacts']['cubin_sha256']] = (proof, json.loads(prior[prefix+'/json.stdout']), prior[prefix+'/lines.stdout'].decode())

def versioned_source(commit, name):
    return subprocess.check_output(['git', '-C', str(a.repo), 'show', commit+':'+name])


def j(files, name):
    return json.loads(files[name])


for files, install, package, count, commit, inputs in [
        (old, 'install-v1', 'package-call-model', 24, '3b237e8fb054d4d7b24cef0c2b9c06169fbc0e6f', 'check-input-v1'),
        (new, 'install-v2', 'package-call-model-v2', 25, '39e95f42135a0ec761ede1b4a0f8f1524fb3188e', 'check-input-v2')]:
    need(j(files, package+'/terminal.json')['state'] == 'build_passed_not_device_qualified', 'Package terminal')
    bridge = j(files, package+'/native-byte-bridge.json')
    need(bridge['byte_equal'] and len(bridge['native_members']) == 7, 'Native byte bridge')
    prefix = 'runs/'+install+'/'
    need(j(files, prefix+'terminal.json')['returncode'] == 0, 'Independent installation failed')
    need(j(files, prefix+'output/result.json')['installed_members_byte_verified'] == 607, 'Installed byte coverage')
    need(files['installed/timeline_nvidia_machine.py'] == versioned_source(commit,
         'Profiler/python/flagtree_profiler/timeline_nvidia_machine.py'), 'Installed mapper source identity')
    need(files[inputs+'/test_nvidia_machine_map.py'] == versioned_source(commit,
         'tests/timeline/test_nvidia_machine_map.py'), 'Actually executed CPU test identity')
    for mode in ['normal', 'optimized']:
        log = files[prefix+'output/machine-contract-'+mode+'.stderr.log']
        need(('Ran '+str(count)+' tests').encode() in log and b'\nOK\n' in log, 'CPU contracts')
        need(b'4 passed' in files[prefix+'output/public-contract-'+mode+'.stdout.log'], 'Public CPU contracts')
        result = j(files, prefix+'output/reinspection-'+mode+'/result.json')
        need(result['actual_math_launches'] == 0 and len(result['objects']) == 7, 'Real object coverage')
        need(sum(r['counter_pcs'] for r in result['objects']) == 140 and
             sum(r['synchronization_sites'] for r in result['objects']) == 13, 'Real static inventory coverage')
        for row in result['objects']:
            proof = j(files, prefix+'output/reinspection-'+mode+'/'+row['cubin_sha256']+'.json')
            need(proof['static_model_version'] == 1 and not proof['clock_qualified'] and
                 not proof['region_boundaries_verified'], 'Static inventory overclaims qualification')
            need(all(len(c['direct_call_sites']) == 1 for c in proof['counter_call_sites']), 'Exact direct caller missing')
            original, disassembly, text = actual_objects[row['cubin_sha256']]
            need(proof['artifacts'] == original['artifacts'] and proof['counter_pcs'] == original['counter_pcs'], 'Actual object/counter identity changed')
            functions = {f['function-name']: f for f in disassembly[1]}
            for call in proof['call_sites']:
                function = functions[call['function']]
                ins = function['sass-instructions'][(call['pc']-function['start'])//16]
                need(ins['opcode'] == call['opcode'] and ins.get('predicate') == call['predicate'] and
                     ins['operands'] == call['callee'] and call['target_status'] == 'resolved', 'Call differs from original actual JSON')
                pattern = r'/\*0*'+format(call['pc'], 'x')+r'\*/\s*'
                if call['predicate']: pattern += re.escape(call['predicate'])+r'\s+'
                pattern += re.escape(call['opcode'])+r'\s+`\('+re.escape(call['callee'])+r'\)\s*;'
                need(re.search(pattern, text), 'Call differs from original actual text')
            actual_sync = {(f['function-name'], f['start']+16*i): ins
                           for f in functions.values() for i, ins in enumerate(f['sass-instructions'])
                           if ins['opcode'].startswith(('BAR.', 'MEMBAR', 'DEPBAR', 'LDGDEPBAR', 'WARPSYNC'))}
            need(set(actual_sync) == {(x['function'], x['pc']) for x in proof['synchronization_sites']}, 'Actual synchronization coverage')
            for site in proof['synchronization_sites']:
                ins = actual_sync[(site['function'], site['pc'])]
                need(ins['opcode'] == site['opcode'] and ins.get('operands', '') == site['operands'] and
                     ins.get('predicate') == site['predicate'], 'Synchronization operands differ from actual object')

need(j(old, 'runs/public-call-model-v1/terminal.json')['returncode'] == 0, 'Public real math terminal')
public = j(old, 'runs/public-call-model-v1/output/call-model-result.json')
need(public['actual_math_launches'] == public['captures'] == 5 and
     public['static_call_references'] == public['static_getter_references'] == 80, 'Public math/call coverage')
types = j(old, 'runs/public-call-model-v1/output/result.json')
need(types['canonical_intervals'] == 320 and all(r['exact_cpu_math'] and r['state'] == [1, 1, 1]
     for r in types['math']), 'Real dtype math/once result')

need(j(gcu, 'run-v1/terminal.json')['returncode'] == 0, 'GCU job terminal')
need(gcu['input/p01_enflame_dynamic_vertical.py'] == versioned_source(
     '39e95f42135a0ec761ede1b4a0f8f1524fb3188e', 'tests/timeline/p01_enflame_dynamic_vertical.py'), 'GCU executed source')
result = j(gcu, 'run-v1/output/result.json')
need(result['ordinary_math_launches'] == 1 and result['profiled_math_launches'] == 3, 'GCU requested call count')
summary = []
for call in result['calls']:
    k = call['steps']
    prefix = 'run-v1/output/k'+str(k)+'/'
    doc = j(gcu, prefix+'raw/native/capture.observations.json')
    need(len(doc['captures']) == 1, 'GCU invocation isolation')
    capture = doc['captures'][0]
    raw = base64.b64decode(capture['raw_base64'], validate=True)
    need(sha(raw) == capture['raw_sha256'], 'Original GCU bytes SHA')
    write, cap, dropped, flags, stride, payload, attempted, reserved = struct.unpack_from('<8I', raw)
    need(stride == 64 and payload == len(raw) == 32+cap*64 and flags == dropped == reserved == 0 and
         write == attempted == call['events'], 'Actual selected append header')
    metadata = j(gcu, 'run-v1/output/metadata-k'+str(k)+'.json')
    need(metadata['debug_protocol_version'] == 2 and metadata['debug_record_layout'] == 'selected_dynamic_timeline_v1', 'Producer protocol')
    need(metadata['debug_dynamic_selected_program'] == metadata['debug_dynamic_selected_actor'] == 0 and
         metadata['debug_dynamic_sample_every'] == 1, 'Selection or sampling identity')
    runtime = capture['runtime_metadata']
    proof = runtime['profiler_association_evidence']
    need(proof['binary_id'] == metadata['hash'] == call['binary_hash'] and
         proof['invocation_id'] == runtime['profiler_invocation_id'], 'Actual launch/binary association')
    events = [e for e in doc['observations'] if e.get('storage') == 'selected_dynamic_append']
    need(len(events) == write, 'Lost decoded GCU records')
    selected = set(metadata['debug_automatic_plan']['selected_sites'])
    counts = Counter()
    for index, event in enumerate(events):
        kind, zero, site, program, begin, end, duration, actor, sequence, ordinal, commit = struct.unpack_from('<HHIQQQQIIQQ', raw, 32+index*64)
        need(kind == 7 and zero == 0 and site in selected and program == actor == 0 and
             sequence == ordinal == index and commit == 0x465044594e563031 and
             0 < begin <= end < (1 << 46) and duration == end-begin, 'Actual physical GCU payload')
        need((event['site'], event['program'], event['actor'], event['sequence'],
              event['start_tick'], event['end_tick']) == (site, program, actor, index, begin, end), 'Decoded interval differs from bytes')
        need(event['duration_ns'] is None and event['clock']['tick_ns'] is None, 'Unqualified ticks became ns')
        counts[site] += 1
    body_sites = {s for region in metadata['debug_automatic_plan']['control_regions'] if region['repeated']
                  for s in region['selected_sites']}
    need(body_sites and all(counts[s] == k for s in body_sites), 'Runtime loop occurrences do not match real input')
    need(call['state'] == 1 and call['exact_input'], 'Real math/input/once check')
    summary.append(dict(steps=k, events=write, sites=len(counts), repeated_site_counts={str(s): counts[s] for s in body_sites},
                        raw_bytes=len(raw), raw_sha256=sha(raw), binary_id=metadata['hash']))
need(len({c['binary_id'] for c in summary}) == 1 and sum(c['events'] for c in summary) == 42, 'GCU runtime specialization or count')
out = dict(status='actual_call_model_and_gcu_raw_bytes_audited_not_full_P01',
           mapper_cpu_methods_v1=24, mapper_cpu_methods_v2=25, public_cpu_methods_each_mode=4,
           reinspected_real_objects=7, reinspected_static_getters=140, static_synchronization_sites=13,
           public_dtype_math_calls=5, public_dtype_intervals=320, gcu_calls=summary,
           limits=['No region/clock/physical-generation or original-pipeline certification.',
                   'GCU uses existing advanced producer; public common timeline integration still required.',
                   'Perfetto, other backend P01 and final independent qualification remain incomplete.'])
a.output.write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps(out, indent=2))
