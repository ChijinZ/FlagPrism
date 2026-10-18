"""Real native header/count addressing and bounded CPU corruption fixtures."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, units, addresses, control):
    output.mkdir(parents=True)
    originals = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    rejected, reports = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            rejected.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Invalid native record address accepted: ' +
                               name)

    overlap = {
        0: dict(opcode='MOV.64', operands='R0,0x1'),
        16: dict(opcode='MOV.64', operands='R2,0x200000000'),
        32: dict(opcode='LEA', operands='R0,P0,R0,R2,0x3'),
        48: dict(opcode='LEA.HI.X', operands='R1,R0,R3,R1,0x3,P0'),
        64: dict(opcode='STG.E.64', operands='desc[UR0][R0.64],RZ'),
        80: dict(opcode='EXIT', operands='')
    }
    reject(
        'low_address_output_clobbers_high_word_input', lambda: addresses._Wide(
            overlap, addresses._predecessors(overlap)).pair(64, 'R0'))

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        capture = json.loads((timeline / item['capture_file']).read_text())
        machine = units.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / capture['owner']['binary_id']
        ptx = [
            r for r in capture['metadata']['timeline_artifacts']
            if r['retained_file'].endswith('.ptx')
        ]
        if len(ptx) != 1:
            raise RuntimeError('Ambiguous original PTX')
        inputs = dict(machine_map=machine,
                      sass_lines=(base / 'lines.stdout').read_bytes(),
                      sass_json=(base / 'json.stdout').read_bytes(),
                      ptx=(timeline / ptx[0]['retained_file']).read_bytes(),
                      plan=capture['owner']['plan'])
        proof = addresses.derive_record_addresses(**inputs)
        binding = addresses.load_record_ordinal_bindings(
            timeline, capture, proof)
        if not binding['rows'] or binding[
                'relative_record_ordinal_binding_verified'] is not True:
            raise RuntimeError('Actual raw native count binding missing')
        if proof['absolute_raw_slot_binding_verified'] or proof[
                'time_flows_qualified']:
            raise RuntimeError(
                'Relative addressing granted absolute storage or time flow')
        functions = control._bound_functions(machine, inputs['sass_lines'],
                                             inputs['sass_json'])
        for report in proof['functions']:
            body = functions[report['function']]
            graph = addresses._predecessors(body)
            counter = report['header']['value_register']
            wide = addresses._Wide(body, graph, counter=counter)
            header_register = report['header']['address_register']
            lo = wide._one_definition(report['header']['pc'], header_register)
            hi = wide._one_definition(
                report['header']['pc'],
                addresses._registers(header_register, 2)[1])
            if body[lo]['opcode'] != 'LEA' or body[hi]['opcode'] != 'LEA.HI.X':
                raise RuntimeError(
                    'Actual header-address epoch fixture not exercised')
            changed = copy.deepcopy(body)
            lower = addresses._compact(changed[lo]['operands']).split(',')
            upper = addresses._compact(changed[hi]['operands']).split(',')
            lower[2], upper[1], upper[
                3] = counter, counter, addresses._registers(counter, 2)[1]
            changed[lo]['operands'], changed[hi]['operands'] = ','.join(
                lower), ','.join(upper)
            reject(
                'header_base_depends_on_mutable_count_epoch',
                lambda: addresses._published_header_address(
                    addresses._Wide(changed, graph, counter=counter), report[
                        'header']))
            counter_batches = [
                r for r in report['batches']
                if r['mode'] == 'published_counter_relative'
            ]
            if not counter_batches:
                raise RuntimeError(
                    'Actual runtime loop counter batch not exercised')
            for batch in counter_batches:
                low, high = batch['address_low_pc'], batch['address_high_pc']
                register = addresses._compact(
                    body[low]['operands']).split(',')[0]
                for mode in ('wrong_carry', 'wrong_index_high', 'wrong_shift'):
                    changed = copy.deepcopy(body)
                    fields = addresses._compact(
                        changed[high]['operands']).split(',')
                    if mode == 'wrong_carry':
                        fields[-1] = 'PT'
                    elif mode == 'wrong_index_high':
                        fields[3] = fields[1].removesuffix('.reuse')
                    else:
                        fields[4] = '0x1'
                    changed[high]['operands'] = ','.join(fields)
                    reject(
                        mode, lambda: addresses._Wide(
                            changed, graph, counter=counter).pair(
                                batch['field_store_pcs'][0], register))
                changed = copy.deepcopy(body)
                protected = low + 16
                changed[protected] = dict(
                    opcode='ISETP.EQ.AND',
                    operands=addresses._compact(
                        body[low]['operands']).split(',')[1] + ',PT,RZ,RZ,PT')
                reject(
                    'carry_overwritten_between_words',
                    lambda: addresses._Wide(changed, graph, counter=counter).
                    pair(batch['field_store_pcs'][0], register))
            for mode in ('increment_before_address', 'different_update_count',
                         'missing_update', 'duplicate_update'):
                batches, writes = copy.deepcopy(
                    report['batches']), copy.deepcopy(report['count_writes'])
                if mode == 'increment_before_address':
                    next(b for b in batches
                         if b['mode'] == 'published_counter_relative'
                         )['address_high_pc'] = max(body)
                elif mode == 'different_update_count':
                    next(w for w in writes
                         if w['mode'] == 'append_batch_count')['value'] += 1
                elif mode == 'missing_update':
                    writes = [
                        w for w in writes if w['mode'] != 'append_batch_count'
                    ]
                else:
                    writes.append(
                        copy.deepcopy(
                            next(w for w in writes
                                 if w['mode'] == 'append_batch_count')))
                    # A different actual PC is required to avoid a duplicate
                    # dictionary entry masking this fixture.
                    writes[-1]['pc'] = max(body)
                reject(
                    mode, lambda: addresses._check_batch_control(
                        body, graph, counter, batches, writes))
        wrong = copy.deepcopy(proof)
        wrong['binary_id'] = '0' * 64
        reject(
            'wrong_binary', lambda: addresses.load_record_ordinal_bindings(
                timeline, capture, wrong))
        wrong = copy.deepcopy(proof)
        wrong['functions'][0]['batches'][0]['site_ids'].reverse()
        reject(
            'wrong_native_batch_order',
            lambda: addresses.load_record_ordinal_bindings(
                timeline, capture, wrong))
        wrong = copy.deepcopy(proof)
        wrong['functions'][0]['batches'][0]['count'] -= 1
        reject(
            'incomplete_native_batch',
            lambda: addresses.load_record_ordinal_bindings(
                timeline, capture, wrong))
        broken = dict(inputs, ptx=inputs['ptx'] + b'\n// changed original\n')
        failed = addresses.inspect_record_addresses(**broken)
        if failed.get(
                'status'
        ) != 'unverified_native_record_addresses_or_pattern' or not failed[
                'implementation_sha256']:
            raise RuntimeError(
                'Changed original did not preserve unverified fingerprints')
        reports.append(
            dict(proof=proof,
                 dynamic_batches=len(binding['rows']),
                 dynamic_records=sum(r[4] for r in binding['rows'])))
    if originals != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Original capture changed')
    (output / 'result.json').write_text(
        json.dumps(dict(reports=reports,
                        rejected=rejected,
                        negative_checks=len(rejected),
                        original_files_unchanged=len(originals),
                        application_replayed=False),
                   indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from flagtree.profiler import timeline_unit_nvidia_late, timeline_nvidia_late_addresses, timeline_nvidia_control
    run(args.timeline,
        args.output,
        units=timeline_unit_nvidia_late,
        addresses=timeline_nvidia_late_addresses,
        control=timeline_nvidia_control)
