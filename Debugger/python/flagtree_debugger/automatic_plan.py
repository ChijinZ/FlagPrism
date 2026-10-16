"""Bounded selection from compiler operations and actual control-region owners.

Control ancestry is compiler metadata, never inferred from names, locations,
operation ID intervals or earlier executions. Selection precedes instrumentation.
"""
from collections.abc import Mapping
import re

AUTOMATIC_PLAN_VERSION = 4
CONTROL_FLOW_METADATA_VERSION = 2


def _category(item):
    operation = item['mlirOpName']
    return ('memory' if any(
        part in operation
        for part in ('load', 'store', 'atomic',
                     'copy')) else 'aggregate' if any(
                         part in operation
                         for part in ('reduce', 'scan', 'dot')) else 'compute')


def _region_key(owner):
    return owner['controlId'], owner['regionIndex'], owner['blockIndex']


def _representative_rank(item):
    # Prefer data observations to index bookkeeping, while retaining a real
    # unconditional body/header position when that is all a region contains.
    category = _category(item)
    element = item.get('result', {}).get('elementDtype', '')
    return (0 if category == 'memory' else
            1 if category == 'aggregate' else 2 if element.startswith(
                ('f', 'bf')) else 3)


def _source_line(item):
    # Prefer structured compiler positions where present. Current tracked tables
    # retain actual MLIR locations; parse a FileLineCol leaf without treating
    # different columns on the same source line as separate source regions.
    file, line = item.get('sourceFile'), item.get('sourceLine')
    if isinstance(file, str) and file and type(line) is int and line > 0:
        return file, line
    match = re.search(r'"((?:[^"\\]|\\.)+)":([0-9]+):[0-9]+',
                      item.get('sourceLoc', ''))
    return (match.group(1), int(match.group(2))) if match else None


def plan_operations(table, max_sites):
    if type(max_sites) is not int or not 1 <= max_sites <= 128:
        raise ValueError('automatic max_sites must be an integer in [1,128]')
    rows = list(table.values()) if isinstance(table, Mapping) else list(table)
    inventory, eligible, regions = [], [], {}
    for row in rows:
        identity = row.get('opId', row.get('op_id'))
        operation = row.get('mlirOpName', '')
        reason = None
        if type(identity) is not int or not 0 < identity <= 0x7fffffff:
            reason = 'not_a_device_observer_id'
        elif row.get('isSyntheticStatementCapture') or operation.startswith(
            ('flagtree.debug.', 'flagtree_debug.')):
            # Metadata-only operand captures do not name an instrumentable IR
            # operation. Their IDs cannot be passed to the timeline selector.
            reason = 'synthetic_metadata_without_device_operation'
        elif operation == 'arith.constant' or operation.startswith(
            ('scf.', 'cf.', 'func.')):
            reason = 'control_container_or_nonobservable_operation'
        elif '.call' in operation or operation.endswith(('return', 'yield')):
            reason = 'call_or_terminator'
        elif not operation:
            reason = 'missing_compiler_operation'
        item = dict(row,
                    automatic_eligible=reason is None,
                    exclusion_reason=reason,
                    selected=False)
        inventory.append(item)
        ancestry = item.get('controlFlowAncestors', [])
        for index, owner in enumerate(ancestry):
            key = _region_key(owner)
            group = regions.setdefault(
                key, dict(owner, eligible_sites=[], direct_sites=[]))
            if reason is None:
                group['eligible_sites'].append(identity)
                if index == len(ancestry) - 1:
                    group['direct_sites'].append(identity)
        if reason is None:
            eligible.append(item)
    if not eligible:
        raise ValueError(
            'Automatic observation found no instrumentable internal operations; compiler inventory retained in metadata'
        )
    by_id = {item.get('opId', item.get('op_id')): item for item in eligible}
    chosen, selected_ids = [], set()

    def select(item, reason):
        identity = item.get('opId', item.get('op_id'))
        if identity in selected_ids or len(chosen) >= max_sites:
            return
        item['selected'] = True
        item['selection_reason'] = reason
        selected_ids.add(identity)
        chosen.append(item)

    # A public kernel's real entry block is compiler evidence, unlike an empty
    # SCF ancestry list (which also occurs in combiners and other functions).
    # These anchors describe their own scalar activity, never a branch outcome.
    if max_sites >= 3:
        entry_candidates = [
            item for item in eligible
            if item.get('isKernelEntryContext') is True
            and not item.get('controlFlowAncestors')
            and item.get('result', {}).get('valueKind') == 'scalar'
            and item.get('sourceLoc') not in (None, '', 'loc(unknown)')
        ]
        entry_candidates.sort(key=lambda item: not item.get(
            'isControlConditionComputation', False))
        if entry_candidates:
            first = entry_candidates[0]
            select(first, 'verified_kernel_entry_scalar_context')
            remaining = entry_candidates[1:]
            if remaining:
                first_line = _source_line(first)
                second = next(
                    (item
                     for item in remaining if _source_line(item) is not None
                     and _source_line(item) != first_line), remaining[0])
                select(second, 'verified_kernel_entry_scalar_context')

    # Reserve a representative for each actual repeating region before using
    # the remaining budget for class diversity. While condition and body are
    # distinct IR regions, as are the two arms of a conditional.
    ordered_regions = sorted(regions.values(),
                             key=lambda owner:
                             (not owner['repeated'], owner['controlId'], owner[
                                 'regionIndex'], owner['blockIndex']))
    for group in ordered_regions:
        candidates = group['direct_sites'] or group['eligible_sites']
        if candidates and not selected_ids.intersection(candidates):
            candidate = min((by_id[site] for site in candidates),
                            key=_representative_rank)
            select(candidate, 'control_flow_region_representative')
    buckets = {}
    for item in eligible:
        if item.get('opId', item.get('op_id')) not in selected_ids:
            buckets.setdefault(_category(item), []).append(item)
    while len(chosen) < min(max_sites, len(eligible)):
        for category in ('memory', 'aggregate', 'compute'):
            bucket = buckets.get(category, [])
            if bucket and len(chosen) < max_sites:
                select(bucket.pop(0 if len(chosen) % 2 == 0 else -1),
                       'bounded_class_round_robin')
    for group in ordered_regions:
        group['selected_sites'] = sorted(
            selected_ids.intersection(group['eligible_sites']))
        direct = selected_ids.intersection(group['direct_sites'])
        group['coverage_status'] = (
            'no_eligible_operation' if not group['eligible_sites'] else
            'direct_representative' if direct else 'descendant_only'
            if group['selected_sites'] else 'budget_excluded')
        group['coverage_reason'] = (
            'no_instrumentable_internal_operation_in_region' if
            not group['eligible_sites'] else 'actual_region_position_selected'
            if direct else 'no_direct_eligible_operation'
            if group['selected_sites'] else 'site_budget_exhausted')
    for item in eligible:
        if not item['selected']:
            item['selection_reason'] = 'site_budget_excluded'
    return {
        'schema_version': 1,
        'policy': 'bounded_control_flow_then_class',
        'policy_version': AUTOMATIC_PLAN_VERSION,
        'control_flow_metadata_version': CONTROL_FLOW_METADATA_VERSION,
        'max_sites': max_sites,
        'candidate_count': len(eligible),
        'selected_sites':
        [item.get('opId', item.get('op_id')) for item in chosen],
        'control_regions': ordered_regions,
        'inventory': inventory
    }
