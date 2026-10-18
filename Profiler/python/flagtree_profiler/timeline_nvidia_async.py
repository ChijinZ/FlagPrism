"""Mechanism facts for complete NVIDIA cp.async observer streams.

Rule source: NVIDIA PTX ISA, cp.async.commit_group and cp.async.wait_group:
https://docs.nvidia.com/cuda/parallel-thread-execution/#data-movement-and-conversion-instructions-cp-async-wait-group-cp-async-wait-all

Facts describe recorded logical submit attempts, commits and wait guarantees.
They do not establish hardware busy, byte movement, clock alignment, physical
buffer generations or instruction placement. Those require separate evidence.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json

MODEL = 'nvidia.cp_async.groups.v1'
SHARED_VIEW_MODEL = 'nvidia.cp_async.shared_views.v2'
ROLES = frozenset({
    'nvidia.cp_async.submit', 'nvidia.cp_async.commit', 'nvidia.cp_async.wait'
})


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{label} must be an integer >= {minimum}')
    return value


def _id(identity, kind, *parts):
    payload = json.dumps([*identity, kind, *parts],
                         ensure_ascii=False,
                         separators=(',', ':')).encode()
    return kind + '-' + hashlib.sha256(payload).hexdigest()


def validate_shared_view_associations(decoded, plan):
    """Bind physical payloads to the operation that owns each compiler site.

    An address is scoped to one invocation/program, not a globally unique
    allocation. Equal origins do not prove equal extents or disjoint storage.
    """
    version = decoded.get('record_version')
    if (type(version) is not int or version not in (2, 3)
            or type(plan.get('timeline_record_version')) is not int
            or plan['timeline_record_version'] != version):
        raise ValueError('Mismatched shared-view record ABI')
    sites = {
        row['scope_id']: row
        for row in plan['inventory'] if row.get('selected') is True
    }
    for record in decoded['records']:
        site = sites.get(record.get('site'))
        if site is None:
            raise ValueError(
                'Shared-view record has no selected compiler site')
        association = record.get('association')
        expected = version == 3 and site.get('operation') in (
            'ttg.async_copy_global_to_local', 'ttg.local_load')
        if not expected:
            if association is not None:
                raise ValueError(
                    'Unexpected shared-view payload on compiler operation')
            continue
        if type(association) is not dict or set(association) != {
                'kind', 'address_space', 'byte_address', 'raw_byte_offset',
                'raw_byte_length'
        }:
            raise ValueError('Missing or malformed shared-view payload')
        if (association['kind'] != 'nvidia.shared_view_origin'
                or type(association['address_space']) is not int
                or association['address_space'] != 3
                or type(association['byte_address']) is not int
                or not 0 <= association['byte_address'] <= 0xffffffff
                or type(association['raw_byte_offset']) is not int
                or association['raw_byte_offset']
                != record['raw_byte_offset'] + 16
                or type(association['raw_byte_length']) is not int
                or association['raw_byte_length'] != 16
                or record.get('raw_byte_length') != 32):
            raise ValueError(
                'Shared-view payload has invalid address or raw provenance')


def derive_cp_async_facts(decoded, plan, *, capture_id, invocation_id,
                          binary_id):
    """Return identity-bound logical group facts, never verified time arrows.

    Incomplete observer streams are retained as status but yield no groups or
    edges: a missing commit cannot shift all later group generations. No
    iteration or buffer-slot identity is inferred from occurrence numbers.
    """
    identity = (capture_id, invocation_id, binary_id)
    if any(type(v) is not str or not v for v in identity):
        raise ValueError(
            'Capture, invocation and binary identities are required')
    if (type(decoded) is not dict or type(plan) is not dict
            or type(decoded.get('record_version')) is not int
            or decoded.get('record_version') not in (2, 3)
            or type(plan.get('timeline_plan_version')) is not int
            or plan.get('timeline_plan_version') != 1
            or type(plan.get('timeline_record_version')) is not int
            or plan.get('timeline_record_version') != decoded['record_version']
            or type(plan.get('schema_version')) is not int
            or plan.get('schema_version') != 2
            or plan.get('binary_id') != binary_id):
        raise ValueError(
            'Unsupported record/plan/inventory for cp.async facts')
    inventory = plan.get('inventory')
    if type(inventory) is not list:
        raise ValueError('Compiler inventory is required')
    sites = {}
    mechanism_count = 0
    for row in inventory:
        if type(row) is not dict or type(row.get('selected')) is not bool:
            raise ValueError('Malformed compiler candidate')
        role = row.get('timeline_mechanism')
        if role is not None:
            if type(role
                    ) is not str or role not in ROLES or not row['selected']:
                raise ValueError(
                    'Unknown or excluded required async mechanism')
            mechanism_count += 1
            if role == 'nvidia.cp_async.wait':
                if _integer(row.get('timeline_wait_pending'),
                            'wait pending') > 7:
                    raise ValueError('Unsupported cp.async wait operand')
        if row['selected']:
            site = _integer(row.get('scope_id'), 'scope id')
            if site >= 1 << 31 or site in sites:
                raise ValueError('Compiler manifest aliases scope identities')
            sites[site] = row
    count = _integer(plan.get('timeline_async_boundary_count'),
                     'async boundary count')
    if mechanism_count != count:
        raise ValueError(
            'Async boundary inventory does not match compiler count')

    observers = decoded.get('observers')
    records = decoded.get('records')
    if type(observers) is not list or not observers or type(
            records) is not list:
        raise ValueError('Decoded observer and record lists are required')
    streams, rows, offsets = defaultdict(list), {}, set()
    for observer in observers:
        if type(observer) is not dict:
            raise ValueError('Malformed observer descriptor')
        key = tuple(_integer(observer.get(k), k) for k in ('program', 'warp'))
        if key in rows or type(observer.get('complete')) is not bool:
            raise ValueError('Duplicate or invalid observer')
        rows[key] = observer
    if type(decoded.get('complete')) is not bool or decoded['complete'] != all(
            row['complete'] for row in rows.values()):
        raise ValueError('Capture completeness disagrees with observer status')
    for record in records:
        if type(record) is not dict:
            raise ValueError('Invalid decoded record')
        key = tuple(_integer(record.get(k), k) for k in ('program', 'warp'))
        if key not in rows:
            raise ValueError('Record has no invocation observer')
        for field in ('site', 'sequence', 'tick', 'raw_byte_offset'):
            _integer(record.get(field), field)
        if (record['site'] not in sites or record.get('raw_byte_length')
                != (16 if decoded['record_version'] == 2 else 32)
                or record['tick'] >= 1 << 64 or record['raw_byte_offset'] % 4
                or record['raw_byte_offset'] in offsets):
            raise ValueError(
                'Record does not reference a known full-width site')
        if record.get('phase') not in ('entry', 'exit'):
            raise ValueError('Unknown record phase')
        offsets.add(record['raw_byte_offset'])
        streams[key].append(record)
    validate_shared_view_associations(decoded, plan)

    operations, groups, waits, dependencies, statuses = [], [], [], [], []
    view_generations, view_loads = [], []
    evidence = {}
    for key, observer in rows.items():
        stream = streams[key]
        written = _integer(observer.get('written_records'), 'written_records')
        retained = _integer(observer.get('retained_records'),
                            'retained_records')
        overwritten = _integer(observer.get('overwritten_records'),
                               'overwritten_records')
        if len(stream) != retained or retained > written:
            raise ValueError('Observer record counts disagree')
        saturated = observer.get('saturated')
        if type(saturated) is not bool:
            raise ValueError('Invalid saturation status')
        complete = observer['complete']
        if complete != (not saturated and overwritten == 0):
            raise ValueError('Observer loss status is inconsistent')
        if not complete:
            statuses.append({
                'program':
                key[0],
                'warp':
                key[1],
                'status':
                'incomplete_no_dependency_facts',
                'reason':
                'missing_history_cannot_assign_group_generations'
            })
            continue
        if written != retained or [r['sequence']
                                   for r in stream] != list(range(written)):
            raise ValueError(
                'Complete stream has missing or reordered records')
        if any(a['tick'] > b['tick'] for a, b in zip(stream, stream[1:])):
            raise ValueError('Complete observer timer regressed')
        stack, pairs = [], []
        for record in stream:
            if record['phase'] == 'entry':
                stack.append(record)
                continue
            if not stack or stack[-1]['site'] != record['site']:
                raise ValueError(
                    'Observer interval boundaries are not properly nested')
            begin = stack.pop()
            if record['tick'] < begin['tick']:
                raise ValueError('Observer interval timer regressed')

            def view_key(row):
                value = row.get('association')
                return None if value is None else (value['kind'],
                                                   value['address_space'],
                                                   value['byte_address'])

            if view_key(begin) != view_key(record):
                raise ValueError(
                    'Region entry and exit use different shared-view identities'
                )
            if sites[record['site']].get('timeline_mechanism') or (
                    decoded['record_version'] == 3
                    and sites[record['site']].get('operation')
                    == 'ttg.local_load'):
                pairs.append((begin, record))
        if stack:
            raise ValueError('Complete observer stream has unclosed regions')
        # Async IR operations here have no regions, so their own intervals must
        # not overlap; enclosing logical region intervals are harmless.
        pairs.sort(key=lambda pair: pair[0]['sequence'])
        last_end = -1
        uncommitted, history = [], []
        latest_views, view_counts, group_guarantees, operation_refs = {}, defaultdict(
            int), {}, {}
        guaranteed_prefix = 0
        for begin, end in pairs:
            if begin['sequence'] <= last_end:
                raise ValueError(
                    'Async mechanism intervals overlap in one observer')
            last_end = end['sequence']
            site = sites[begin['site']]
            role = site.get('timeline_mechanism') or 'nvidia.shared.load'
            operation_id = _id(identity, 'operation', *key, begin['sequence'],
                               end['sequence'])
            refs = []
            for record in (begin, end):
                rid = _id(identity, 'record', *key, record['sequence'])
                evidence[rid] = {
                    'program': key[0],
                    'warp': key[1],
                    'sequence': record['sequence'],
                    'site': record['site'],
                    'phase': record['phase'],
                    'tick': record['tick'],
                    'raw_byte_offset': record['raw_byte_offset'],
                    'raw_byte_length': record['raw_byte_length']
                }
                refs.append(rid)
            operation = {
                'id': operation_id,
                'program': key[0],
                'warp': key[1],
                'site': begin['site'],
                'mechanism': role,
                'begin_tick': begin['tick'],
                'end_tick': end['tick'],
                'record_ids': refs,
                'buffer_slot': None,
                'iteration_id': None
            }
            operations.append(operation)
            operation_refs[operation_id] = refs
            association = begin.get('association')
            if association is not None:
                operation['shared_view'] = association
                operation['buffer_slot'] = association['byte_address']
            if role == 'nvidia.cp_async.submit':
                uncommitted.append(operation)
            elif role == 'nvidia.cp_async.commit':
                group_id = _id(identity, 'group', *key, len(history))
                group = {
                    'id':
                    group_id,
                    'program':
                    key[0],
                    'warp':
                    key[1],
                    'logical_commit_ordinal':
                    len(history),
                    'generation_basis':
                    'complete_recorded_commit_stream',
                    'commit_operation_id':
                    operation_id,
                    'submit_operation_ids': [v['id'] for v in uncommitted],
                    'may_include_predicated_empty_submits':
                    True,
                    'empty_recorded_submit_set':
                    not uncommitted,
                    'record_ids':
                    [r for v in uncommitted for r in v['record_ids']] + refs
                }
                groups.append(group)
                history.append(group)
                by_origin = defaultdict(list)
                for submit in uncommitted:
                    if 'shared_view' in submit:
                        by_origin[submit['shared_view']
                                  ['byte_address']].append(submit)
                for address, submits in by_origin.items():
                    generation = {
                        'id':
                        _id(identity, 'shared-view-generation', *key, address,
                            view_counts[address]),
                        'program':
                        key[0],
                        'warp':
                        key[1],
                        'byte_address':
                        address,
                        'generation':
                        view_counts[address],
                        'group_id':
                        group_id,
                        'generation_basis':
                        'runtime_shared_view_origin_and_complete_commit_stream',
                        'submit_operation_ids': [v['id'] for v in submits],
                        'may_be_predicated_empty':
                        True,
                        'record_ids':
                        [r for v in submits for r in v['record_ids']] + refs
                    }
                    view_counts[address] += 1
                    latest_views[address] = generation
                    view_generations.append(generation)
                uncommitted = []
            elif role == 'nvidia.cp_async.wait':
                pending = site['timeline_wait_pending']
                direct_prefix = max(0, len(history) - pending)
                newly_guaranteed = history[guaranteed_prefix:direct_prefix]
                guaranteed_prefix = max(guaranteed_prefix, direct_prefix)
                wait = {
                    'id':
                    operation_id,
                    'program':
                    key[0],
                    'warp':
                    key[1],
                    'pending_group_limit':
                    pending,
                    'direct_coverage_commit_range': [0, direct_prefix],
                    'newly_guaranteed_group_ids':
                    [v['id'] for v in newly_guaranteed],
                    'known_guaranteed_commit_range': [0, guaranteed_prefix],
                    'record_ids':
                    refs
                }
                waits.append(wait)
                # Emit each group's first completion guarantee once. Repeated
                # waits reference compact ranges, avoiding a quadratic trace.
                for group in newly_guaranteed:
                    group_guarantees[group['id']] = operation_id
                    dependencies.append({
                        'id':
                        _id(identity, 'dependency', group['id'], operation_id),
                        'producer_id':
                        group['id'],
                        'consumer_id':
                        operation_id,
                        'relation':
                        'commit_group_completion_covered_by_wait',
                        'new_guarantee':
                        True,
                        'record_ids':
                        group['record_ids'] + refs,
                        'time_arrow_verified':
                        False,
                    })
            else:
                address = association['byte_address']
                generation = latest_views.get(address)
                outstanding = any(
                    v.get('shared_view', {}).get('byte_address') == address
                    for v in uncommitted)
                guarantee = group_guarantees.get(
                    generation['group_id']) if generation else None
                established = generation is not None and guarantee is not None and not outstanding
                view_loads.append({
                    'operation_id':
                    operation_id,
                    'program':
                    key[0],
                    'warp':
                    key[1],
                    'byte_address':
                    address,
                    'generation_id':
                    generation['id'] if established else None,
                    'wait_operation_id':
                    guarantee if established else None,
                    'status':
                    'same_origin_prior_group_wait_covered'
                    if established else 'uncommitted_same_origin' if
                    outstanding else 'no_wait_covered_same_origin_generation',
                    'record_ids':
                    refs + (generation['record_ids'] +
                            operation_refs[guarantee] if established else []),
                    'time_arrow_verified':
                    False
                })
        statuses.append({
            'program':
            key[0],
            'warp':
            key[1],
            'status':
            'complete_logical_mechanism_stream',
            'uncommitted_submit_ids': [v['id'] for v in uncommitted],
            'groups_not_covered_by_observed_wait':
            [v['id'] for v in history[guaranteed_prefix:]]
        })
    return {
        'model':
        SHARED_VIEW_MODEL if decoded['record_version'] == 3 else MODEL,
        'capture_id':
        capture_id,
        'invocation_id':
        invocation_id,
        'binary_id':
        binary_id,
        'record_stream_complete':
        decoded['complete'],
        'operations':
        operations,
        'groups':
        groups,
        'waits':
        waits,
        'dependencies':
        dependencies,
        'records':
        evidence,
        'shared_view_generations':
        view_generations,
        'shared_view_loads':
        view_loads,
        'observers':
        statuses,
        'time_arrow_verified':
        False,
        'limits': [
            'Submit scopes are logical attempts, not engine activity',
            'Shared-view generations describe committed attempts; masks may suppress byte movement',
            'Equal view origins do not prove equal footprints, disjoint storage or safe reuse',
            'Clock and final instruction boundary evidence are separate gates'
        ]
    }
