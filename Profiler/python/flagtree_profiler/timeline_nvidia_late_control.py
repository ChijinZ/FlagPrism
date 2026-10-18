"""Final-object wait order for late inline counter readers.

Requires a freshly validated counter_map. These are conditional native control
facts, not source-cost, raw-value provenance, participation or clock proofs.
"""
import re
import hashlib
from pathlib import Path

from .timeline_nvidia_control import (_bound_functions, _branch, _check_region,
                                      _compact, _need)

MODEL = 'nvidia.cp_async.late_wait_control.v1'


def _single_entry(body, first, last):
    """No external control edge may enter after the sampled entry reader."""
    for pc, row in body.items():
        opcode = row['opcode']
        target = None
        if opcode in ('BRA', 'BRA.U'):
            _, target = _branch(row)
        elif opcode.startswith('BSSY'):
            match = re.fullmatch(r'B\d+,0x([0-9a-fA-F]+)',
                                 _compact(row.get('operands', '')))
            _need(match is not None, 'Unknown reconvergence destination')
            target = int(match[1], 16)
        elif (opcode.startswith(
            ('BRX', 'JMP', 'JMX', 'CALL', 'RET')) or row.get(
                'other-attributes', {}).get('control-flow') == 'True'):
            _need(opcode.startswith(('BSYNC', 'EXIT')),
                  'Unknown function control can bypass the inline reader')
        if target is not None and not first <= pc < last:
            _need(
                not first < target <= last,
                'External control edge enters after the inline entry reader')


def derive_late_wait_control(*, machine_map, sass_lines, sass_json, plan):
    _need(
        machine_map.get('status')
        == 'counter_mapping_complete_region_unverified'
        and machine_map.get('marker_flavor') == 'late-v1'
        and machine_map.get('expected_sm') == [12, 0]
        and plan.get('binary_id') == machine_map.get('binary_id'),
        'Late wait control requires the matching actual SM120 object map')
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    counters = {}
    for row in machine_map['counter_pcs']:
        counters.setdefault((row['site_id'], row['phase']), []).append(row)
    results = []
    for site in plan['sites']:
        if site['kind'] != 'wait_bracket':
            continue
        result = dict(site_id=site['site_id'],
                      status='unverified',
                      source_region_qualified=False,
                      record_value_provenance_verified=False,
                      clock_qualified=False,
                      participation_verified=False)
        try:
            _need(
                site['record_semantics'] == 'observer_issue_bracket'
                and site['members'] and all(member['native_operation'] ==
                                            'llvm.nvvm.cp.async.wait.group'
                                            for member in site['members']),
                'Late wait site does not describe native cp.async.wait.group')
            endpoints = []
            for phase in ('entry', 'exit'):
                rows = counters.get((site['site_id'], phase), [])
                _need(
                    len(rows) == 1,
                    'Missing or ambiguous static inline reader')
                row = rows[0]
                endpoints.append(dict(row,
                                      predicate=row.get('sass_predicate')))
            begin, end = endpoints
            _need(begin['function'] == end['function'],
                  'Late readers are in different functions')
            body = functions[begin['function']]
            _single_entry(body, begin['pc'], end['pc'])
            waits = [(pc, row) for pc, row in body.items()
                     if begin['pc'] < pc < end['pc']
                     and row['opcode'] == 'DEPBAR.LE']
            _need(
                len(waits) == 1,
                'Missing or ambiguous native wait between inline readers')
            operand = re.fullmatch(r'SB0,0x([0-7])',
                                   _compact(waits[0][1].get('operands', '')))
            _need(operand is not None,
                  'Unrecognized native pending-group limit')
            checked = _check_region(begin, end, body, int(operand[1], 16))
            result.update(status='late_wait_control_order_checked',
                          function=begin['function'],
                          begin_reader_pc=checked.pop('begin_call_pc'),
                          end_reader_pc=checked.pop('end_call_pc'),
                          **checked)
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    from . import timeline_nvidia_control
    return dict(
        model=MODEL,
        binary_id=machine_map['binary_id'],
        sites=results,
        helper_rules_sha256=hashlib.sha256(
            Path(timeline_nvidia_control.__file__).read_bytes()).hexdigest(),
        proof_scope='native_wait_control_order_between_late_inline_readers',
        source_region_qualified=False,
        record_value_provenance_verified=False,
        participation_verified=False,
        clock_qualified=False,
        hardware_overlap_verified=False,
        time_flows_qualified=False)


def inspect_late_wait_control(**inputs):
    try:
        return derive_late_wait_control(**inputs)
    except (ValueError, KeyError, TypeError) as error:
        return dict(model=MODEL,
                    binary_id=inputs['machine_map'].get('binary_id'),
                    status='unverified_control_inputs_or_pattern',
                    sites=[],
                    reason=str(error),
                    exception=type(error).__name__,
                    source_region_qualified=False,
                    clock_qualified=False,
                    hardware_overlap_verified=False,
                    time_flows_qualified=False)
