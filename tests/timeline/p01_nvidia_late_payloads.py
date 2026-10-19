"""Actual AS3 payload/byte-group bindings, epoch and corrupted-raw negatives."""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path


def run(timeline,
        output,
        *,
        units,
        payloads,
        control,
        require_early_coalesced=True):
    output.mkdir(parents=True)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    rejected, reports = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError) as error:
            rejected.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Invalid native payload accepted: ' + name)

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        cap = load_capture_file(timeline / item['capture_file'])
        machine = units.load_late_machine_map(timeline, cap)
        base = timeline / 'machine' / cap['owner']['binary_id']
        ptx = [
            r for r in cap['metadata']['timeline_artifacts']
            if r['retained_file'].endswith('.ptx')
        ]
        if len(ptx) != 1:
            raise RuntimeError('Ambiguous original PTX')
        args = dict(machine_map=machine,
                    sass_lines=(base / 'lines.stdout').read_bytes(),
                    sass_json=(base / 'json.stdout').read_bytes(),
                    ptx=(timeline / ptx[0]['retained_file']).read_bytes(),
                    plan=cap['owner']['plan'])
        proof = payloads.derive_shared_payloads(**args)
        expected = [
            s for s in args['plan']['sites'] if s['kind'] in payloads._KINDS
        ]
        if len(proof['sites']) != len(expected) or any(
                row['status'] != 'native_shared_payload_words_checked'
                for row in proof['sites']):
            raise RuntimeError('Actual native shared payload failed: ' +
                               str(proof))
        functions = control._bound_functions(machine, args['sass_lines'],
                                             args['sass_json'])
        for site in proof['sites']:
            body = functions[site['function']]
            graph = payloads._predecessors(body)
            dom = payloads._dominators(graph)
            words = payloads._Words(body,
                                    graph,
                                    dom,
                                    operation_pc=site['operation_pc'],
                                    store_pc=site['payload_store_pc'],
                                    normalize_invariants=True)
            value = words.value(site['payload_store_pc'],
                                site['payload_registers'][0])
            address = __import__('re').search(r'\[[^\]]+\]',
                                              site['native_operands'])[0]
            expected_low = words.arena.add(
                words.address(site['operation_pc'], address),
                site['native_byte_suboffset'])
            if value != expected_low or value == words.arena.add(
                    expected_low, 4):
                raise RuntimeError('Native address offset not preserved')
            changed = copy.deepcopy(body)
            writer = next(iter(graph[site['payload_store_pc']]))
            changed[writer] = dict(opcode='MOV',
                                   operands=site['payload_registers'][0] +
                                   ',0x0')
            altered = payloads._Words(changed,
                                      graph,
                                      dom,
                                      operation_pc=site['operation_pc'],
                                      store_pc=site['payload_store_pc'],
                                      normalize_invariants=True)
            # Same native address and the actual changed reaching store value
            # must not be certified equal. The fixture is never device code.
            wrong = altered.value(site['payload_store_pc'],
                                  site['payload_registers'][0])
            desired = altered.arena.add(
                altered.address(site['operation_pc'], address),
                site['native_byte_suboffset'])
            if wrong == desired:
                raise RuntimeError('Clobbered address word accepted')
            rejected.append(
                dict(case='reaching_payload_low_clobber',
                     site_id=site['site_id']))
        binding = payloads.load_shared_payload_bindings(timeline, cap, proof)
        if binding[
                'status'] != 'native_shared_payload_domains_and_groups_checked' or binding[
                    'collective_byte_model_status'] != 'dynamic_byte_model_consistent':
            raise RuntimeError('Actual raw byte model/group binding missing')
        raw = (timeline / cap['raw_file']).read_bytes()
        for program, actor, ordinal, site_id, offset, value, group, first in binding[
                'rows']:
            if struct.unpack_from('<Q', raw,
                                  offset)[0] != value or not 0 <= group < len(
                                      binding['groups']) or first > ordinal:
                raise RuntimeError(
                    'Raw payload/native group reference differs from actual bytes'
                )
        merged = [s for s in proof['sites'] if len(s['source_origins']) > 1]
        early_coalesced = bool(merged) and any(
            s['native_operation_before_source_entry'] for s in merged)
        if require_early_coalesced and not early_coalesced:
            raise RuntimeError(
                'Actual coalesced source mapping case not exercised')
        if any(not s['native_byte_coverage_complete'] for s in merged):
            raise RuntimeError('Coalesced native byte footprint incomplete')
        fixture = output / ('raw-fixtures-' + cap['owner']['invocation_id'])
        fixture.mkdir()

        def corrupt(name, witness, payload):
            changed = bytearray(raw)
            struct.pack_into('<Q', changed, witness[4], payload)
            path = fixture / (name + '.raw')
            path.write_bytes(changed)
            copy_cap = copy.deepcopy(cap)
            copy_cap.update(raw_file=path.name,
                            raw_sha256=hashlib.sha256(changed).hexdigest())
            reject(
                name, lambda: payloads.load_shared_payload_bindings(
                    fixture, copy_cap, proof))

        by_id = {s['site_id']: s for s in proof['sites']}
        cp = next(r for r in binding['rows']
                  if by_id[r[3]]['kind'] == 'copy_submit_after')
        corrupt('invalid_native_source_valid_bytes', cp,
                (cp[5] & 0xffffffff) | (8 << 32))
        shared_base = struct.unpack_from(
            '<Q', raw, 4 * cap['owner']['plan']['actors'] * 8)[0]
        invalid = shared_base + cap['metadata']['compiler_metadata']['shared']
        corrupt('shared_address_outside_actual_allocation', cp,
                (cp[5] & 0xffffffff00000000) | invalid)
        folded = next((r for r in binding['rows']
                       if by_id[r[3]]['native_byte_suboffset'] == 4), None)
        if require_early_coalesced and folded is None:
            raise RuntimeError('Required coalesced subrange fixture missing')
        if folded is not None:
            corrupt('coalesced_source_subranges_disagree', folded,
                    folded[5] + 4)
        other = copy.deepcopy(proof)
        other['binary_id'] = '0' * 64
        reject(
            'other_binary_payload_proof',
            lambda: payloads.load_shared_payload_bindings(
                timeline, cap, other))
        reject(
            'changed_original_ptx', lambda: payloads.derive_shared_payloads(
                **dict(args, ptx=args['ptx'] + b'\n')))
        reject(
            'changed_actual_disassembly',
            lambda: payloads.derive_shared_payloads(**dict(
                args, sass_json=args['sass_json'] + b'\n')))
        if any(proof[k] is not False
               for k in ('absolute_raw_slot_binding_verified',
                         'record_value_provenance_verified', 'clock_qualified',
                         'hardware_overlap_verified', 'time_flows_qualified')):
            raise RuntimeError(
                'Native payload words granted unrelated qualification')
        reports.append(
            dict(proof=proof,
                 mapping_fixture=dict(early_coalesced=early_coalesced,
                                      merged_sites=len(merged),
                                      subrange_corruption_exercised=folded
                                      is not None),
                 raw_binding_summary=dict(
                     identity=binding['identity'],
                     rows=len(binding['rows']),
                     groups=binding['groups'],
                     byte_model=binding['collective_byte_model_status'])))
    # A value from the preceding iteration must not equal the current operation.
    body = {
        0: dict(opcode='MOV', operands='R2,0x0'),
        16: dict(opcode='NOP'),
        32: dict(opcode='MOV', operands='R10,R2'),
        48: dict(opcode='IADD3', operands='R2,PT,PT,R2,0x1,RZ'),
        64: dict(opcode='LDGSTS.E.BYPASS.128',
                 operands='[R2],desc[UR0][R8.64],P0'),
        80: dict(opcode='MOV', operands='R14,R10'),
        96: dict(opcode='STG.E.64', operands='desc[UR0][R8.64],R14'),
        112: dict(opcode='BRA', operands='0x10', predicate='@P0'),
        128: dict(opcode='EXIT')
    }
    graph = payloads._predecessors(body)
    words = payloads._Words(body,
                            graph,
                            payloads._dominators(graph),
                            operation_pc=64,
                            store_pc=96)
    if words.value(64, 'R2') == words.value(96, 'R14'):
        raise RuntimeError('Loop-carried previous/current epochs collapsed')
    if words.cut != 16 or 'R2' not in words.mutable:
        raise RuntimeError('Actual mutable loop-header input not retained')
    invariant = copy.deepcopy(body)
    invariant[0] = dict(opcode='MOV', operands='R8,0x5')
    invariant[32] = dict(opcode='MOV', operands='R10,R8')
    invariant[64]['operands'] = '[R8],desc[UR0][R12.64],P0'
    graph = payloads._predecessors(invariant)
    words = payloads._Words(invariant,
                            graph,
                            payloads._dominators(graph),
                            operation_pc=64,
                            store_pc=96)
    if words.value(64, 'R8') != words.value(96, 'R14'):
        raise RuntimeError('Valid loop-invariant alias rejected')
    # Large native straight-line bodies must not retain quadratic sets.
    chain = {
        pc: ({pc - 16} if pc else set())
        for pc in range(0, 8192 * 16, 16)
    }
    dominators = payloads._dominators(chain)
    last = max(chain)
    if dominators.depth(last) != 8192 or dominators[last] != set(chain):
        raise RuntimeError('Large native dominator graph failed')
    if original != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Original actual artifacts changed')
    result = dict(reports=reports,
                  rejected=rejected,
                  negative_checks=len(rejected),
                  original_files_unchanged=len(original),
                  application_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return dict(captures=len(reports),
                sites=[len(r['proof']['sites']) for r in reports],
                rows=[r['raw_binding_summary']['rows'] for r in reports],
                negative_checks=len(rejected))


def main():
    from flagtree.profiler import timeline_unit_nvidia_late as units
    from flagtree.profiler import timeline_nvidia_late_payloads as payloads
    from flagtree.profiler import timeline_nvidia_control as control
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument(
        '--general-mapping',
        action='store_true',
        help=
        'Check arbitrary native mapping; run the default separately on the early-coalesced regression fixture'
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.timeline,
                args.output,
                units=units,
                payloads=payloads,
                control=control,
                require_early_coalesced=not args.general_mapping)))


if __name__ == '__main__':
    main()
