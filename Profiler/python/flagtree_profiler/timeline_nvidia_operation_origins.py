"""Compiler operation origins in retained NVIDIA native source locations.

Location identity is distinct from elapsed source cost, participation and
hardware completion. A lowering may have several native instructions per
origin; only the separately checked finite matrix rule requires one HMMA.
"""
import hashlib
import json
from pathlib import Path
import re

from .timeline_nvidia_control import _bound_functions, _need

MARKER_FILE = '__flagprism_native_origin_v1__'


def derive_operation_origins(*, machine_map, source_lines, sass_json, plan):
    _need(
        type(plan.get('native_origin_marker_version')) is int
        and plan['native_origin_marker_version'] == 1,
        'No supported compiler operation-origin inventory')
    _need(
        type(source_lines) is bytes and len(source_lines) <= 32 * 1024 * 1024,
        'Native source locations exceed their budget')
    _need(machine_map['binary_id'] == plan.get('binary_id'),
          'Operation origins belong to a different binary')
    # Check every instruction/operand against the same object-bound native
    # JSON. Source annotations are a separately retained vendor-tool output.
    source_map = dict(
        machine_map,
        artifacts=dict(
            machine_map['artifacts'],
            sass_lines_sha256=hashlib.sha256(source_lines).hexdigest()))
    functions = _bound_functions(source_map, source_lines, sass_json)
    inventory, unavailable = {}, []
    for site in plan['sites']:
        for index, member in enumerate(site['members']):
            marker = member.get('native_origin_marker') or {}
            _need(
                type(marker.get('version')) is int and marker['version'] == 1,
                'Unsupported operation-origin marker')
            identity = dict(site_id=site['site_id'], member_index=index)
            if marker.get('status') == 'unavailable_no_debug_scope':
                unavailable.append(identity)
                continue
            line = marker.get('line')
            _need(
                marker.get('status') == 'compiler_location_assigned'
                and marker.get('file') == MARKER_FILE and type(line) is int
                and 1 <= line <= 65535 and type(marker.get('column')) is int
                and marker['column'] == 1,
                'Invalid compiler operation-origin marker')
            _need(line not in inventory,
                  'Duplicate compiler operation-origin ID')
            inventory[line] = dict(**identity, origin_line=line, locations=[])
    function, origin = None, None
    unknown_rows = 0
    for text in source_lines.decode('utf-8').splitlines():
        section = re.match(r'^\s*\.section\s+([^,\s]+)', text)
        if section:
            name = section[1]
            function = name[6:] if name.startswith('.text.') else None
            origin = None
        label = re.fullmatch(r'\s*([^\s:]+):\s*', text)
        if label and label[1] in functions:
            function, origin = label[1], None
        if text.strip().startswith('//## File '):
            origin = None
            location = re.fullmatch(r'\s*//## File "([^"]+)", line (\d+)\s*',
                                    text)
            if location and location[1] in (MARKER_FILE, './' + MARKER_FILE):
                line = int(location[2])
                if line == 0:
                    unknown_rows += 1
                else:
                    _need(line in inventory,
                          'Native location has an unknown origin ID')
                    origin = line
        instruction = re.match(r'\s*/\*([0-9a-fA-F]+)\*/', text)
        if instruction and origin is not None:
            pc = int(instruction[1], 16)
            _need(function in functions and pc in functions[function],
                  'Native origin location leaves its instruction function')
            point = dict(function=function,
                         pc=pc,
                         opcode=functions[function][pc]['opcode'])
            inventory[origin]['locations'].append(point)
    rows = list(inventory.values())
    return dict(
        schema_version=1,
        status=('native_operation_locations_mapped' if any(
            r['locations']
            for r in rows) else 'unavailable_native_operation_locations'),
        binary_id=machine_map['binary_id'],
        cubin_sha256=machine_map['artifacts']['cubin_sha256'],
        sass_json_sha256=machine_map['artifacts']['sass_json_sha256'],
        source_lines_sha256=hashlib.sha256(source_lines).hexdigest(),
        origins=rows,
        unavailable_members=unavailable,
        missing_origin_lines=[
            r['origin_line'] for r in rows if not r['locations']
        ],
        compiler_unknown_rows=unknown_rows,
        source_regions_qualified=False,
        source_cost_qualified=False,
        participation_qualified=False,
        hardware_busy_qualified=False,
        implementation_sha256=hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest())


def matrix_member_locations(plan, boundaries, origins):
    _need(
        origins.get('binary_id') == plan.get('binary_id')
        and isinstance(plan.get('binary_id'), str),
        'Matrix member origins belong to a different binary')
    by_member = {
        (r['site_id'], r['member_index']): r
        for r in origins['origins']
    }
    sites = {s['site_id']: s for s in plan['sites']}
    results = []
    for boundary in boundaries:
        result = dict(site_id=boundary['site_id'],
                      status='unverified',
                      source_cost_qualified=False,
                      participation_verified=False)
        try:
            _need(boundary['status'] == 'matrix_issue_control_order_checked',
                  'Matrix issue boundaries are unverified')
            site = sites[boundary['site_id']]
            members = []
            for index, member in enumerate(site['members']):
                _need(
                    'mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32'
                    in member['native_operation'],
                    'Unsupported LLVM matrix member')
                row = by_member[site['site_id'], index]
                points = [
                    p for p in row['locations']
                    if p['opcode'].startswith(('HMMA', 'IMMA', 'MMA', 'HGMMA',
                                               'UTCMMA'))
                ]
                _need(
                    len(points) == 1
                    and points[0]['opcode'] == 'HMMA.16816.F32'
                    and points[0]['function'] == boundary['function'],
                    'LLVM member lacks one exact native HMMA location')
                members.append(
                    dict(member_index=index,
                         origin_line=row['origin_line'],
                         native_pc=points[0]['pc']))
            pcs = [m['native_pc'] for m in members]
            _need(
                len(pcs) == len(set(pcs))
                and set(pcs) == {r['native_pc']
                                 for r in boundary['issues']},
                'LLVM members differ from the bounded native matrix issues')
            result.update(status='matrix_member_native_locations_checked',
                          members=members)
        except (ValueError, KeyError, TypeError) as error:
            result['reason'] = str(error)
        results.append(result)
    return results


def load_operation_origins(directory, capture, machine_map, boundaries):
    """Recheck retained source output, never invoke a compiler/tool offline."""
    from .timeline_store import read_artifact
    plan = capture['owner']['plan']
    try:
        _need(
            type(plan.get('native_origin_marker_version')) is int
            and plan['native_origin_marker_version'] == 1,
            'Legacy capture has no compiler operation-origin markers')
        base = 'machine/' + machine_map['binary_id']
        saved = json.loads(
            read_artifact(directory, base + '/operation-origins.json'))
        source = read_artifact(directory, base + '/source-lines.stdout')
        for key, value in [
            ('binary_id', machine_map['binary_id']),
            ('cubin_sha256', machine_map['artifacts']['cubin_sha256']),
            ('sass_json_sha256', machine_map['artifacts']['sass_json_sha256']),
            ('source_lines_sha256', hashlib.sha256(source).hexdigest())
        ]:
            _need(
                saved.get(key) == value,
                'Retained native source identity differs: ' + key)
        counter = json.loads(
            read_artifact(directory, base + '/counter-map.json'))
        _need(
            saved.get('tool_sha256') == counter.get('tool_sha256')
            and isinstance(saved.get('tool_sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', saved['tool_sha256']) is not None,
            'Native source locations lack their matching disassembler identity'
        )
        report = derive_operation_origins(machine_map=machine_map,
                                          source_lines=source,
                                          sass_json=read_artifact(
                                              directory,
                                              base + '/json.stdout'),
                                          plan=plan)
        report['matrix_members'] = matrix_member_locations(
            plan, boundaries, report)
        return report
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        return dict(status='unverified_native_operation_origins',
                    reason=str(error),
                    source_regions_qualified=False,
                    source_cost_qualified=False,
                    participation_qualified=False,
                    hardware_busy_qualified=False)
