"""Finite mandatory compute-prefix check on retained SDK decoding; no replay.

It does not establish complete CFG coverage, external entries, hardware order,
source exclusive cost or completion. No general ISA decoding is attempted.
"""
import csv
import hashlib
import json
from pathlib import Path

root = Path('/tmp/chijin-timeline-r063-ascend/runs/existing-vector-model-v3/output')
model = next((root / 'SDK-MODEL-output').glob('OPPROF_*'))
base = int((model / 'dump/pc_start_addr.txt').read_text().strip(), 16)
path = model / 'simulator/core0.veccore0/core0.veccore0_instr_exe.csv'
rows = {int(r['addr']) - base: r for r in csv.DictReader(path.open())}


def prefix(decoded, entry, exit, expected):
    if entry >= exit or decoded.get(entry, {}).get('instr') != 'MOV_XD_SPR':
        raise ValueError('Missing clock entry')
    if 'SPR:SYS_CNT,' not in decoded[entry]['detail']:
        raise ValueError('Entry is not SYS_CNT')
    cursor, native = entry + 4, []
    while cursor < exit:
        row = decoded.get(cursor)
        if row is None:
            raise ValueError('Retained decoding has a gap before the required compute prefix ends')
        opcode = row['instr']
        if opcode.startswith('JUMP') or opcode == 'END':
            raise ValueError('Control transfer before all required native compute operations')
        if opcode in expected:
            native.append((cursor, opcode))
        if [op for _, op in native] == expected:
            return native
        cursor += 4
    raise ValueError('Clock exit precedes required native computation')


expected = ['VMULS', 'VADDS']
entry, exit = 0x12d0, 0x1334
actual = prefix(rows, entry, exit, expected)
negative = []
for name, changed, stop in [
    ('exit_before_add', rows, 0x130c),
    ('missing_prefix_instruction', {k: v for k, v in rows.items() if k != 0x12ec}, exit),
    ('branch_before_multiply', {**rows, 0x12e4: {**rows[0x12e4], 'instr': 'JUMP'}}, exit),
]:
    try:
        prefix(changed, entry, stop, expected)
    except ValueError as error:
        negative.append(dict(name=name, rejected=True, reason=str(error)))
    else:
        raise RuntimeError('Negative prefix fixture accepted: ' + name)
print(json.dumps(dict(
    status='finite_decoded_compute_prefix_checked',
    actual_ELF_sha256=hashlib.sha256((model/'dump/aicore_binary.o').read_bytes()).hexdigest(),
    SDK_instruction_csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    entry_pc=entry, exit_pc=exit, required_native_operations=actual,
    complete_contiguous_decoding_through_last_required_operation=True,
    no_control_transfer_in_that_prefix=True,
    negative_fixtures=negative,
    SDK_child_failure_139_remains=True,
    all_path_region_proof=False,
    external_entry_coverage_proved=False,
    hardware_dynamic_order_proved=False,
    product_qualification_changed=False,
    simulation_or_application_replayed=False,
), indent=2))
