"""Retained actual machine timer/store checks and control/value negative fixtures."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, units, values, control):
    output.mkdir(parents=True)
    original = {
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
            raise RuntimeError('Timer store value negative accepted: ' + name)

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(timeline / item['capture_file'])
        machine = units.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / capture['owner']['binary_id']
        ptx_rows = [
            r for r in capture['metadata']['timeline_artifacts']
            if r['retained_file'].endswith('.ptx')
        ]
        if len(ptx_rows) != 1:
            raise RuntimeError('Ambiguous original PTX')
        lines, native = (base / 'lines.stdout').read_bytes(), (
            base / 'json.stdout').read_bytes()
        args = dict(machine_map=machine,
                    sass_lines=lines,
                    sass_json=native,
                    ptx=(timeline / ptx_rows[0]['retained_file']).read_bytes(),
                    plan=capture['owner']['plan'])
        report = values.derive_timer_store_values(**args)
        if not report['sites'] or any(
                r['status'] != 'timer_to_native_store_values_checked'
                for r in report['sites']):
            raise RuntimeError(
                'Actual full-width timer/store values failed: ' + str(report))
        functions = control._bound_functions(machine, lines, native)
        for result in report['sites']:
            reader = next(r for r in machine['counter_pcs']
                          if (r['site_id'], r['phase']) == (result['site_id'],
                                                            result['phase']))
            body = functions[result['function']]
            graph = values._predecessors(body)
            for store in result['stores']:
                for word, register in enumerate(store['word_registers']):
                    checked = dict(reader=reader,
                                   store_pc=store['store_pc'],
                                   word_register=register,
                                   word_index=word)
                    reject(
                        'swapped_timer_word', lambda: values.check_timer_word(
                            body, graph, **dict(checked, word_index=1 - word)))
                    altered = copy.deepcopy(body)
                    altered[reader['pc']] = dict(opcode='CS2R',
                                                 operands=reader['operands'],
                                                 predicate='@P0')
                    reject(
                        'predicated_getter', lambda: values.check_timer_word(
                            altered, graph, **checked))
                    # Inject a reaching constant overwrite at a real predecessor
                    # of this store. No unsafe fixture is run on the device.
                    predecessor = next(iter(graph[store['store_pc']]))
                    altered = copy.deepcopy(body)
                    altered[predecessor] = dict(opcode='MOV',
                                                operands=register + ',0x7')
                    reject(
                        'reaching_constant_clobber',
                        lambda: values.check_timer_word(
                            altered, graph, **checked))
                    altered_graph = copy.deepcopy(graph)
                    altered_graph[store['store_pc']].add(min(body))
                    reject(
                        'path_bypasses_getter',
                        lambda: values.check_timer_word(
                            body, altered_graph, **checked))
        reject(
            'original_ptx_changed', lambda: values.derive_timer_store_values(
                **dict(args, ptx=args['ptx'] + b'\n')))
        reject(
            'actual_disassembly_changed', lambda: values.
            derive_timer_store_values(**dict(args, sass_json=native + b'\n')))
        altered = copy.deepcopy(machine)
        altered['counter_pcs'].append(copy.deepcopy(altered['counter_pcs'][0]))
        reject(
            'duplicate_getter_identity', lambda: values.
            derive_timer_store_values(**dict(args, machine_map=altered)))
        if any(report[k] is not False
               for k in ('record_storage_binding_verified',
                         'record_value_provenance_verified',
                         'payload_provenance_verified',
                         'source_region_qualified', 'clock_qualified',
                         'hardware_overlap_verified', 'time_flows_qualified')):
            raise RuntimeError('Timer value witness granted unrelated rights')
        for helper in (values._single_entry, values._bound_functions,
                       values._lex):
            file = Path(helper.__code__.co_filename)
            if report['implementation_sha256'].get(
                    file.name) != hashlib.sha256(
                        file.read_bytes()).hexdigest():
                raise RuntimeError(
                    'Called native rule implementation is not fingerprinted')
        reports.append(report)
    # A real move must pass, including simultaneous overlapping MOV.64.
    fixture = {
        0: dict(opcode='CS2R', operands='R2,SR_GLOBALTIMERLO'),
        16: dict(opcode='MOV.64', operands='R3,R2'),
        32: dict(opcode='STG.E.64', operands='desc[UR0][R8.64],R3'),
        48: dict(opcode='EXIT')
    }
    reader = dict(pc=0, sass_predicate=None)
    for word, register in enumerate(('R3', 'R4')):
        values.check_timer_word(fixture,
                                values._predecessors(fixture),
                                reader=reader,
                                store_pc=32,
                                word_register=register,
                                word_index=word)
    altered = copy.deepcopy(fixture)
    altered[16]['predicate'] = '@P0'
    reject(
        'predicated_move_does_not_preserve_both_paths',
        lambda: values.check_timer_word(altered,
                                        values._predecessors(altered),
                                        reader=reader,
                                        store_pc=32,
                                        word_register='R3',
                                        word_index=0))
    if values._destinations(
            dict(opcode='LOP3.LUT', operands='PT,R3,RZ,RZ,0x0,!PT')) != ['R3']:
        raise RuntimeError('Discarded predicate hid real scalar destination')
    reconvergence = {
        0:
        dict(opcode='NOP'),
        16:
        dict(opcode='BSSY.RECONVERGENT',
             operands='B0,0x60',
             **{'other-attributes': {
                 'control-flow': 'True'
             }}),
        32:
        dict(opcode='CS2R', operands='R2,SR_GLOBALTIMERLO'),
        48:
        dict(opcode='STG.E.64', operands='desc[UR0][R8.64],R2'),
        64:
        dict(opcode='NOP'),
        80:
        dict(opcode='BSYNC.RECONVERGENT',
             operands='B0',
             **{'other-attributes': {
                 'control-flow': 'True'
             }}),
        96:
        dict(opcode='EXIT')
    }
    values._predecessors(reconvergence)
    changed = copy.deepcopy(reconvergence)
    changed[16]['operands'] = 'B0,0x50'
    reject('wrong_reconvergence_target', lambda: values._predecessors(changed))
    changed = copy.deepcopy(reconvergence)
    changed[64] = dict(opcode='BSSY.RECONVERGENT', operands='B0,0x60')
    reject('reconvergence_token_redefined',
           lambda: values._predecessors(changed))
    changed = copy.deepcopy(reconvergence)
    changed[0] = dict(opcode='BRA', operands='0x30', predicate='@P0')
    reject('external_entry_bypasses_reconvergence_setup',
           lambda: values._predecessors(changed))
    if original != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Actual retained originals changed')
    result = dict(reports=reports,
                  negative_checks=len(rejected),
                  rejected=rejected,
                  original_files_unchanged=len(original),
                  device_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return dict(captures=len(reports),
                sites=[len(r['sites']) for r in reports],
                negative_checks=len(rejected))


def main():
    from flagtree.profiler import timeline_unit_nvidia_late as units
    from flagtree.profiler import timeline_nvidia_late_values as values
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
                values=values,
                control=control)))


if __name__ == '__main__':
    main()
