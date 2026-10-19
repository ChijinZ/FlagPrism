"""Read existing SDK model instruction names, never model times as hardware time.

Finite audit of the unchanged already hardware-executed C1 vector ELF. This is
not a product provider, a general ISA decoder, or a simulation-success receipt.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import struct

root = Path('/tmp/chijin-timeline-r063-ascend/runs/existing-vector-model-v3/output')
timeline = Path('/tmp/chijin-timeline-r060-ascend/runs/participation-device-v1/output/device/vector/capture/timeline')
expected_sha = '73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


index = json.loads((timeline / 'index.json').read_text())
capture_path = timeline / index['captures'][0]['capture_file']
capture = json.loads(capture_path.read_text())
binding = json.loads((root / 'binding.json').read_text())
need(sha(capture_path.read_bytes()) == binding['actual_capture_sha256'], 'Capture identity changed')
need(capture['owner']['binary_id'] == binding['actual_binary_id'], 'Binary identity changed')
machine = timeline / 'machine' / binding['actual_binary_id']
model_outputs = list((root / 'SDK-MODEL-output').glob('OPPROF_*'))
need(len(model_outputs) == 1, 'Ambiguous SDK model output')
model = model_outputs[0]
image = (machine / 'loaded.elf').read_bytes()
need(all(sha(p.read_bytes()) == expected_sha for p in [machine / 'loaded.elf', root / 'actual-recorded-vector.elf', model / 'dump/aicore_binary.o']), 'Actual and SDK dumped ELF differ')
need(sha(image) == binding['actual_ELF_sha256'], 'Binding differs from ELF')
need(image[:6] == b'\x7fELF\x02\x01', 'Expected ELF64 little endian')
header = struct.unpack_from('<16sHHIQQQIHHHHHH', image)
section_offset, stride, count, names_index = header[6], header[11], header[12], header[13]
sections = [struct.unpack_from('<IIQQQQIIQQ', image, section_offset + i * stride) for i in range(count)]
names_section = sections[names_index]
names = image[names_section[4]:names_section[4] + names_section[5]]
text = [s for s in sections if names[s[0]:].split(b'\0', 1)[0] == b'.text']
need(len(text) == 1 and text[0][3] == 0, 'Only the actual zero-address single .text layout is supported')
text = text[0]
base_path = model / 'dump/pc_start_addr.txt'
base = int(base_path.read_text().strip(), 16)
instructions_path = model / 'simulator/core0.veccore0/core0.veccore0_instr_exe.csv'
rows = list(csv.DictReader(instructions_path.open()))
pcs = {}
for row in rows:
    pc = int(row['addr']) - base
    need(0 <= pc <= text[5] - 4 and pc % 4 == 0, 'SDK instruction PC outside actual .text')
    need(pc not in pcs, 'SDK aggregation has duplicate PC')
    # Deliberately exclude cycles/running_time and simulation register values.
    pcs[pc] = dict(pc=pc, opcode=row['instr'], pipe=row['pipe'], model_call_count=int(row['call_count']), detail=row['detail'])
need(0 in pcs, 'No executed instruction at the declared text start')
map_path = machine / 'counter-map.json'
clock_map = json.loads(map_path.read_text())
need(clock_map['binary_sha256'] == expected_sha and clock_map['binary_id'] == binding['actual_binary_id'], 'Clock map identity mismatch')
markers, absent_from_csv = [], []
for row in clock_map['counter_pcs']:
    pc = row['pc']
    need(struct.unpack_from('<I', image, text[4] + pc)[0] == row['instruction_word'], 'Existing clock word changed')
    if pc not in pcs:
        absent_from_csv.append(dict(site_id=row['site_id'], phase=row['phase'], pc=pc))
        continue
    actual = pcs[pc]
    need(actual['opcode'] == 'MOV_XD_SPR' and 'SPR:SYS_CNT,' in actual['detail'], 'Actual executed clock marker is not SYS_CNT')
    reg = re.search(r'XD:X(\d+)=', actual['detail'])
    need(reg is not None and int(reg.group(1)) == row['register'], 'Clock destination register differs from map')
    markers.append(dict(site_id=row['site_id'], phase=row['phase'], pc=pc, register=row['register']))

metadata = capture['metadata']['compiler_metadata']
artifacts = metadata['flagprism_ascend_handoff']['artifacts']
need(len(artifacts) == 1, 'Finite probe expects one AIV actor')
artifact = artifacts[0]
manifest = artifact['metadata']
need(json.loads(artifact['manifest_text']) == manifest and sha(artifact['manifest_text'].encode()) == artifact['manifest_sha256'], 'Manifest provenance changed')
need(manifest['runtime_actor_binding']['function'] == 'recurrence', 'Unexpected function')
sites = {s['site_id']: s for s in manifest['dynamic_sites']}
for site in sites.values():
    need(sha(site['original_instructions'].encode()) == site['original_instructions_sha256'], 'Original fragment changed')
marker_by_site = collections.defaultdict(dict)
for row in clock_map['counter_pcs']:
    need(row['phase'] not in marker_by_site[row['site_id']], 'Ambiguous finite clock pair')
    marker_by_site[row['site_id']][row['phase']] = row['pc']
checks = []
for sid, expected_opcodes in [(16, ['VMULS', 'VADDS']), (17, ['MOV_SRC_TO_DST_ALIGN']), (18, ['MOV_SRC_TO_DST_ALIGN'])]:
    pair = marker_by_site[sid]
    need(set(pair) == {'entry', 'exit'}, 'Missing finite boundary')
    start, stop = pair['entry'], pair['exit']
    need(start < stop and start in pcs and stop in pcs, 'Requested boundary not observed in model decode')
    between = [pcs[p] for p in sorted(pcs) if start < p < stop]
    selected = [r for r in between if r['opcode'] in expected_opcodes]
    need([r['opcode'] for r in selected] == expected_opcodes, 'Expected native operation not enclosed')
    need(all(r['pipe'] == ('VECTOR' if sid == 16 else 'MTE3') for r in selected), 'Unexpected native pipeline')
    checks.append(dict(site_id=sid, source_op_id=sites[sid]['source_op_id'], source_line=sites[sid]['line'], original_fragment_sha256=sites[sid]['original_instructions_sha256'], entry_pc=start, exit_pc=stop, decoded_native_instructions=selected, all_model_executed_control_flow_inside=[r for r in between if r['opcode'].startswith('JUMP')], evidence_scope='existing executed PC positions only; no unseen paths, exclusive cost or hardware completion'))
need('vmuls_vs_1d_float' in sites[16]['original_instructions'] and 'vadds_vs_1d_float' in sites[16]['original_instructions'], 'Finite compute fragment does not name the two vector operations')
stdout = (root / 'SDK-MODEL.stdout').read_text()
need('Child process exited with status 139' in stdout, 'Expected SDK child-failure evidence changed')
steps = json.loads((root / 'steps.json').read_text())
result = dict(status='retained_finite_instruction_positions_audited_with_SDK_child_failure_preserved', actual_ELF_sha256=expected_sha, actual_binary_id=binding['actual_binary_id'], capture_sha256=binding['actual_capture_sha256'], SDK_outer_returncode=steps[-1]['returncode'], SDK_child_failure_status=139, simulation_run_success_claimed=False, no_application_or_model_replay=True, no_product_change=True, hardware_durations_or_busy_claimed=False, model_durations_exported=False, text_bytes=text[5], text_load_base=hex(base), SDK_reported_unique_instruction_PCs=len(pcs), SDK_reported_SYS_CNT_marker_PCs=len(markers), mapped_markers_absent_from_retained_SDK_CSV=absent_from_csv, source_position_checks=checks, inputs={str(p):sha(p.read_bytes()) for p in [capture_path, map_path, machine/'dwarf.stdout', model/'dump/aicore_binary.o', base_path, instructions_path, root/'binding.json', root/'steps.json', root/'SDK-MODEL.stdout']})
print(json.dumps(result, indent=2))
