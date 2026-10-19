"""Retained actual record-layout checks and native literal/address negatives."""
import argparse
import copy
import hashlib
import importlib
import json
import struct
from pathlib import Path


def run(timeline, output, *, units, records, control):
    output.mkdir(parents=True)
    originals = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    reports, rejected = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError) as error:
            rejected.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Native field negative accepted: ' + name)

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(timeline / item['capture_file'])
        machine = units.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / capture['owner']['binary_id']
        ptx = [
            r for r in capture['metadata']['timeline_artifacts']
            if r['retained_file'].endswith('.ptx')
        ]
        if len(ptx) != 1:
            raise RuntimeError('Missing original PTX')
        args = dict(machine_map=machine,
                    sass_lines=(base / 'lines.stdout').read_bytes(),
                    sass_json=(base / 'json.stdout').read_bytes(),
                    ptx=(timeline / ptx[0]['retained_file']).read_bytes(),
                    plan=capture['owner']['plan'])
        report = records.derive_record_fields(**args)
        if len(report['sites']) != len(args['plan']['sites']) or any(
                row['status'] != 'native_record_fields_checked'
                for row in report['sites']):
            raise RuntimeError('Actual native record fields failed: ' +
                               str(report))
        functions = control._bound_functions(machine, args['sass_lines'],
                                             args['sass_json'])
        stride = args['plan']['actors'] * 8
        for site in report['sites']:
            fields = site['fields']
            body = functions[site['function']]
            graph = records._predecessors(body)
            for field in fields:
                if field['field'] in ('tag', 'payload'):
                    literal = site['site_id'] if field[
                        'field'] == 'tag' else site['literal_payload']
                    if literal is None:
                        if site['payload_status'] != 'variable_payload_unverified':
                            raise RuntimeError(
                                'Variable payload granted literal qualification'
                            )
                        continue
                    register = field['value_register']
                    reject(
                        'wrong_low_literal_word',
                        lambda: records._constant_word(
                            body,
                            graph,
                            store_pc=field['pc'],
                            register=register,
                            expected=(
                                (literal & 0xffffffff) + 1) & 0xffffffff))
            changed = copy.deepcopy(fields)
            changed[1]['offset'] += 8
            reject(
                'wrong_field_stride',
                lambda: records._stable_field_addresses(body, changed, stride))
            changed = copy.deepcopy(fields)
            changed[2]['offset'] = changed[1]['offset']
            reject(
                'overlapping_time_fields',
                lambda: records._stable_field_addresses(body, changed, stride))
            changed = copy.deepcopy(fields)
            changed[3]['descriptor'] = 'UR254'
            reject(
                'different_field_descriptor',
                lambda: records._stable_field_addresses(body, changed, stride))
            changed = copy.deepcopy(fields)
            changed[0], changed[1] = changed[1], changed[0]
            reject(
                'tag_and_begin_swapped',
                lambda: records._stable_field_addresses(body, changed, stride))
            first = min(row['pc'] for row in fields)
            changed_body = copy.deepcopy(body)
            changed_body[first] = dict(opcode='MOV',
                                       operands=fields[0]['address_register'] +
                                       ',RZ')
            reject(
                'address_low_word_clobber',
                lambda: records._stable_field_addresses(
                    changed_body, fields, stride))
            changed_body = copy.deepcopy(body)
            high = control._registers(fields[0]['descriptor'], 2)[1]
            changed_body[first] = dict(opcode='MOV', operands=high + ',RZ')
            reject(
                'descriptor_high_word_clobber',
                lambda: records._stable_field_addresses(
                    changed_body, fields, stride))
            changed_body = copy.deepcopy(body)
            outside = min(body)
            if outside >= first:
                raise RuntimeError(
                    'Actual record has no preceding control for negative fixture'
                )
            changed_body[outside] = dict(opcode='BRA',
                                         predicate='@P0',
                                         operands=hex(first + 16))
            reject(
                'entry_after_first_record_field',
                lambda: records._stable_field_addresses(
                    changed_body, fields, stride))
            if site['absolute_raw_slot_binding_verified'] is not False:
                raise RuntimeError(
                    'Relative addresses claimed absolute raw ownership')
        reject(
            'original_ptx_changed', lambda: records.derive_record_fields(
                **dict(args, ptx=args['ptx'] + b'\n')))
        reject(
            'original_disassembly_changed',
            lambda: records.derive_record_fields(**dict(
                args, sass_lines=args['sass_lines'] + b'\n')))
        unavailable = records.inspect_record_fields(
            **dict(args, ptx=args['ptx'] + b'\n'))
        file = Path(records.__file__)
        if unavailable.get(
                'status'
        ) != 'unverified_native_record_inputs_or_pattern' or unavailable[
                'implementation_sha256'].get(file.name) != hashlib.sha256(
                    file.read_bytes()).hexdigest():
            raise RuntimeError('Unverified diagnostic lost rule fingerprint')
        for key in ('absolute_raw_slot_binding_verified',
                    'record_storage_binding_verified',
                    'record_value_provenance_verified',
                    'variable_payload_provenance_verified', 'clock_qualified',
                    'hardware_overlap_verified', 'time_flows_qualified'):
            if report[key] is not False:
                raise RuntimeError(
                    'Native relative fields granted unrelated right: ' + key)
        for helper in (records._bound_functions, records._native_lines,
                       records._straight_path, records._predecessors,
                       records._destinations, records._move_source,
                       records._lex):
            path = Path(helper.__code__.co_filename)
            if report['implementation_sha256'].get(
                    path.name) != hashlib.sha256(
                        path.read_bytes()).hexdigest():
                raise RuntimeError(
                    'Called field rule implementation not fingerprinted')
        agreement = records.load_control_payload_agreement(
            timeline, capture, report)
        if agreement[
                'status'] != 'native_control_payloads_consistent' or not agreement[
                    'occurrences']:
            raise RuntimeError(
                'Actual dynamic control payload agreement missing')
        if agreement['identity'] != {
                key: capture['owner'][key]
                for key in ('capture_id', 'invocation_id', 'binary_id')
        }:
            raise RuntimeError(
                'Actual dynamic report crossed invocation scope')
        actual_raw = (timeline / capture['raw_file']).read_bytes()
        for witness in agreement['occurrences']:
            for field, expected in [('raw_tag_span', witness['site_id']),
                                    ('raw_payload_span', witness['value'])]:
                offset, size = witness[field]
                if size != 8 or offset < 0 or offset + size > len(
                        actual_raw) or struct.unpack_from(
                            '<Q', actual_raw, offset)[0] != expected:
                    raise RuntimeError(
                        'Dynamic control witness differs from actual raw bytes'
                    )
        raw_decoder = importlib.import_module(records.__package__ +
                                              '.timeline_nvidia_late_raw')
        decoded = raw_decoder.decode_late_raw(
            capture['owner']['plan'],
            (timeline / capture['raw_file']).read_bytes(),
            slots=capture['owner']['layout']['slots'])
        bad = copy.deepcopy(decoded)
        witness = agreement['occurrences'][0]
        program = next(row for row in bad['programs']
                       if row['program_id'] == witness['program'])
        actor = next(row for row in program['observers']
                     if row['actor'] == witness['actor'])
        actor['events'][witness['ordinal']]['payload'] ^= 1
        reject('dynamic_control_payload_disagrees_with_native_operand',
               lambda: records.validate_control_payloads(report, bad))
        bad = copy.deepcopy(decoded)
        bad['complete'] = False
        reject('incomplete_raw_cannot_claim_control_agreement',
               lambda: records.validate_control_payloads(report, bad))
        bad_report = copy.deepcopy(report)
        bad_report['binary_id'] = '0' * 64
        reject(
            'different_binary_control_report',
            lambda: records.load_control_payload_agreement(
                timeline, capture, bad_report))
        reports.append(dict(fields=report, dynamic=agreement))
    fixture = {
        0: dict(opcode='MOV.64', operands='R2,0x1'),
        16: dict(opcode='STG.E.64', operands='desc[UR0][R8.64],R2'),
        32: dict(opcode='EXIT')
    }
    graph = records._predecessors(fixture)
    for register, expected in [('R2', 1), ('R3', 0)]:
        records._constant_word(fixture,
                               graph,
                               store_pc=16,
                               register=register,
                               expected=expected)
    changed = copy.deepcopy(fixture)
    changed[0]['predicate'] = '@P0'
    reject(
        'literal_definition_may_be_bypassed', lambda: records._constant_word(
            changed, graph, store_pc=16, register='R2', expected=1))
    changed = copy.deepcopy(fixture)
    changed[0]['operands'] = 'R2,0xffffffff'
    # SM120 device cases distinguish 0xffffffff from the full 64-bit all-one
    # literal in both the native disassembly and the stored result.
    for register, expected in [('R2', 0xffffffff), ('R3', 0)]:
        records._constant_word(changed,
                               graph,
                               store_pc=16,
                               register=register,
                               expected=expected)
    reject(
        'wrong_wide_literal_high_word', lambda: records._constant_word(
            changed, graph, store_pc=16, register='R3', expected=0xffffffff))
    uniform = copy.deepcopy(changed)
    uniform[0].update(opcode='UMOV.64', operands='UR2,0xffffffff')
    reject(
        'unverified_uniform_wide_literal', lambda: records._constant_word(
            uniform, graph, store_pc=16, register='UR3', expected=0))
    if originals != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Actual original artifacts changed')
    result = dict(reports=reports,
                  rejected=rejected,
                  negative_checks=len(rejected),
                  original_files_unchanged=len(originals),
                  application_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return dict(captures=len(reports),
                sites=[len(r['fields']['sites']) for r in reports],
                negative_checks=len(rejected))


def main():
    from flagtree.profiler import timeline_unit_nvidia_late as units
    from flagtree.profiler import timeline_nvidia_late_records as records
    from flagtree.profiler import timeline_nvidia_control as control
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.timeline,
                args.output,
                units=units,
                records=records,
                control=control)))


if __name__ == '__main__':
    main()
