"""Actual retained default/sparse objects and count-lifetime corruption cases.

This is an offline CPU check. It never executes or recompiles an application.
"""
import argparse
import copy
import json
from pathlib import Path


def run(timelines, output):
    from flagtree.profiler import timeline_nvidia_late_addresses as addresses
    from flagtree.profiler import timeline_unit_nvidia_late as units
    output.mkdir(parents=True)
    checks, rejected = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError):
            rejected.append(name)
        else:
            raise RuntimeError('Invalid native count accepted: ' + name)

    # Synthetic native CFG: a complete fixed-base batch precedes a branch;
    # one path resets its count, the other publishes the nonzero count. The
    # first batch itself has no earlier stores, so only the zero-reset guard
    # can reject this corruption. This fixture is not device evidence.
    reset = {
        0: dict(opcode='LEA', operands='R0,P0,R2,R4,0x3'),
        16: dict(opcode='LEA.HI.X', operands='R1,R2,R5,R3,0x3,P0'),
        32: dict(opcode='MOV.64', operands='R12,0x1'),
        48: dict(opcode='STG.E.64', operands='desc[UR0][R0.64],R6'),
        64: dict(opcode='STG.E.64', operands='desc[UR0][R0.64+0x8],R8'),
        80: dict(opcode='STG.E.64', operands='desc[UR0][R0.64+0x10],R10'),
        96: dict(opcode='STG.E.64', operands='desc[UR0][R0.64+0x18],R14'),
        112: dict(opcode='BRA', operands='0x90', predicate='@P0'),
        128: dict(opcode='BRA', operands='0xa0'),
        144: dict(opcode='MOV.64', operands='R12,RZ'),
        160: dict(opcode='STG.E.64', operands='desc[UR0][R16.64],R12'),
        176: dict(opcode='EXIT', operands='')
    }
    reset_graph = addresses._predecessors(reset)
    live = addresses._live_count_definitions(reset, reset_graph, 'R12', {160})
    reset_writes = addresses._count_write_inventory(reset, 'R12', live)
    if {r['pc'] for r in reset_writes} != {32, 144}:
        raise RuntimeError(
            'Conditional zero-reset fixture lacks both live paths')
    reset_batch = dict(mode='initial_zero_count',
                       count=1,
                       address_low_pc=0,
                       address_high_pc=16,
                       field_store_pcs=[48, 64, 80, 96])
    addresses._no_prior_recording(reset_graph, 0, {32, 48, 64, 80, 96})
    reject(
        'conditional_zero_reset_after_complete_batch',
        lambda: addresses._check_batch_control(reset, reset_graph, 'R12',
                                               [reset_batch], reset_writes))

    for timeline in timelines:
        for item in json.loads(
            (timeline / 'index.json').read_text())['captures']:
            capture = json.loads((timeline / item['capture_file']).read_text())
            machine = units.load_late_machine_map(timeline, capture)
            base = timeline / 'machine' / capture['owner']['binary_id']
            ptx = [
                r for r in capture['metadata']['timeline_artifacts']
                if r['retained_file'].endswith('.ptx')
            ]
            if len(ptx) != 1:
                raise RuntimeError('Ambiguous actual retained PTX')
            inputs = dict(machine_map=machine,
                          sass_lines=(base / 'lines.stdout').read_bytes(),
                          sass_json=(base / 'json.stdout').read_bytes(),
                          ptx=(timeline /
                               ptx[0]['retained_file']).read_bytes(),
                          plan=capture['owner']['plan'])
            proof = addresses.derive_record_addresses(**inputs)
            binding = addresses.load_record_ordinal_bindings(
                timeline, capture, proof)
            functions = addresses._bound_functions(machine,
                                                   inputs['sass_lines'],
                                                   inputs['sass_json'])
            for report in proof['functions']:
                body = functions[report['function']]
                graph = addresses._predecessors(body)
                counter = report['header']['value_register']
                uses = {report['header']['pc']} | {
                    r['low_pc']
                    for r in report['address_lea_pairs'] if r['counter']
                }
                live = addresses._live_count_definitions(
                    body, graph, counter, uses)
                writes = addresses._count_write_inventory(body, counter, live)
                if writes != report['count_writes']:
                    raise RuntimeError('Live count inventory changed')
                unrelated = [
                    pc for pc, row in body.items()
                    if set(addresses._registers(counter, 2)).intersection(
                        addresses._destinations(row)) and pc not in live
                ]
                append = next(w['pc'] for w in writes
                              if w['mode'] == 'append_batch_count')
                for mode in ('live_high_word_overwrite', 'predicated_live_add',
                             'different_add_input'):
                    changed = copy.deepcopy(body)
                    if mode == 'live_high_word_overwrite':
                        high = addresses._registers(counter, 2)[1]
                        changed[append].update(opcode='MOV',
                                               operands=high + ',0x1')
                    elif mode == 'predicated_live_add':
                        changed[append]['predicate'] = '@P0'
                    else:
                        fields = addresses._compact(
                            changed[append]['operands']).split(',')
                        fields[1] = 'R250'
                        changed[append]['operands'] = ','.join(fields)

                    def inventory(changed=changed):
                        rows = addresses._live_count_definitions(
                            changed, graph, counter, uses)
                        addresses._count_write_inventory(
                            changed, counter, rows)

                    reject(mode, inventory)
                initial = next(b for b in report['batches']
                               if b['mode'] == 'initial_zero_count')
                update = initial['count_update_pc']
                start = min(initial['field_store_pcs'] + [
                    initial['address_low_pc'], initial['address_high_pc'],
                    update
                ])
                for mode, prior in (('repeated_initial_batch',
                                     max(initial['field_store_pcs'])),
                                    ('initial_after_other_batch',
                                     max(pc for b in report['batches']
                                         if b is not initial
                                         for pc in b['field_store_pcs']))):
                    changed_graph = {
                        pc: set(rows)
                        for pc, rows in graph.items()
                    }
                    changed_graph[start].add(prior)
                    reject(
                        mode,
                        lambda changed_graph=changed_graph: addresses.
                        _check_batch_control(body, changed_graph, counter,
                                             copy.deepcopy(report['batches']),
                                             copy.deepcopy(writes)))
                checks.append(
                    dict(binary_id=capture['owner']['binary_id'],
                         function=report['function'],
                         live_count_writes=writes,
                         unrelated_register_writes=unrelated,
                         raw_bound_batches=len(binding['rows'])))
    if not checks or not any(c['unrelated_register_writes'] for c in checks):
        raise RuntimeError('Actual register-reuse case was not exercised')
    (output / 'result.json').write_text(
        json.dumps(dict(
            status='actual_native_count_lifetimes_and_raw_ordinals_passed',
            checks=checks,
            rejected=rejected,
            device_executed=False,
            application_replayed=False,
            source_regions_qualified=False,
            ordinary_pipeline_preservation_qualified=False),
                   indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline',
                        action='append',
                        type=Path,
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.timeline, args.output)


if __name__ == '__main__':
    main()
