"""Recheck late wait brackets against retained actual objects; no device replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, unit, control, raw_decoder):
    output.mkdir(parents=True)
    originals = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    index = json.loads((timeline / 'index.json').read_text())
    reports = []
    for item in index['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(timeline / item['capture_file'])
        machine = unit.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / capture['owner']['binary_id']
        lines, native = (base / 'lines.stdout').read_bytes(), (
            base / 'json.stdout').read_bytes()
        report = control.derive_late_wait_control(
            machine_map=machine,
            sass_lines=lines,
            sass_json=native,
            plan=capture['owner']['plan'])
        sites = {r['site_id']: r for r in report['sites']}
        if not sites or any(r['status'] != 'late_wait_control_order_checked'
                            for r in sites.values()):
            raise RuntimeError('Actual late native wait failed: ' +
                               str(report))
        raw = (timeline / capture['raw_file']).read_bytes()
        decoded = raw_decoder.decode_late_raw(
            capture['owner']['plan'],
            raw,
            slots=capture['owner']['layout']['slots'])
        occurrences = 0
        for program in decoded['programs']:
            for actor in program['observers']:
                for event in actor['events']:
                    if event['site_id'] in sites:
                        if event['payload'] != sites[
                                event['site_id']]['pending_group_limit']:
                            raise RuntimeError(
                                'Actual dynamic wait operand contradicts native machine wait'
                            )
                        occurrences += 1
        if occurrences == 0:
            raise RuntimeError('No actual dynamic wait occurrences')
        corrupt = copy.deepcopy(machine)
        counter = next(r for r in corrupt['counter_pcs']
                       if r['site_id'] in sites)
        corrupt['counter_pcs'].append(copy.deepcopy(counter))
        denied = control.derive_late_wait_control(
            machine_map=corrupt,
            sass_lines=lines,
            sass_json=native,
            plan=capture['owner']['plan'])
        if all(r['status'] == 'late_wait_control_order_checked'
               for r in denied['sites']):
            raise RuntimeError('Duplicate inline reader accepted')
        corrupt_lines = control.inspect_late_wait_control(
            machine_map=machine,
            sass_lines=lines + b'\n',
            sass_json=native,
            plan=capture['owner']['plan'])
        if corrupt_lines.get(
                'status') != 'unverified_control_inputs_or_pattern':
            raise RuntimeError('Changed machine inputs accepted')
        reports.append(
            dict(invocation=capture['owner']['invocation_id'],
                 dynamic_wait_occurrences=occurrences,
                 control=report))
    # Explicit CPU control fixtures. These are not compiled/device positives.
    begin, end = dict(pc=0x100), dict(pc=0x150)
    body = {
        0x100: dict(opcode='CS2R'),
        0x110: dict(opcode='NOP'),
        0x120: dict(opcode='DEPBAR.LE', operands='SB0,0x1'),
        0x130: dict(opcode='NOP'),
        0x140: dict(opcode='NOP'),
        0x150: dict(opcode='CS2R')
    }
    control._check_region(begin, end, body, 1)
    rejected = []
    variants = [('wait_bypass', 0x110, dict(opcode='BRA', operands='0x150')),
                ('wrong_wait_operand', 0x120,
                 dict(opcode='DEPBAR.LE', operands='SB0,0x0')),
                ('predicated_wait', 0x120,
                 dict(opcode='DEPBAR.LE', operands='SB0,0x1',
                      predicate='@P0')),
                ('missing_wait', 0x120, dict(opcode='NOP'))]
    for label, pc, row in variants:
        changed = copy.deepcopy(body)
        changed[pc] = row
        try:
            control._check_region(begin, end, changed, 1)
        except ValueError as error:
            rejected.append(dict(case=label, reason=str(error)))
        else:
            raise RuntimeError('Invalid control fixture accepted: ' + label)
    changed = copy.deepcopy(body)
    changed[0x80] = dict(opcode='BRA', operands='0x140')
    try:
        control._single_entry(changed, begin['pc'], end['pc'])
    except ValueError as error:
        rejected.append(
            dict(case='external_entry_after_wait', reason=str(error)))
    else:
        raise RuntimeError('External reader bypass accepted')
    for file, digest in originals.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Original actual capture changed')
    result = dict(
        status=
        'actual_final_object_wait_control_and_dynamic_operands_passed_not_clock_or_time_flows',
        reports=reports,
        cpu_control_fixtures_rejected=rejected,
        originals_unchanged=len(originals),
        device_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    from flagtree.profiler import timeline_unit_nvidia_late as unit
    from flagtree.profiler import timeline_nvidia_late_control as control
    from flagtree.profiler import timeline_nvidia_late_raw as raw_decoder
    run(a.timeline,
        a.output,
        unit=unit,
        control=control,
        raw_decoder=raw_decoder)


if __name__ == '__main__':
    main()
