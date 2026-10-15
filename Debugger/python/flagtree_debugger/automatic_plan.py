"""Bounded automatic selection from compiler-assigned, per-binary operations.

This runs after the real metadata pass; identifiers are never reused across
specializations. Selection reduces actual instrumentation, not report rows.
"""
from collections.abc import Mapping


def plan_operations(table, max_sites):
    if type(max_sites) is not int or not 1 <= max_sites <= 128:
        raise ValueError('automatic max_sites must be an integer in [1,128]')
    rows = list(table.values()) if isinstance(table, Mapping) else list(table)
    inventory, eligible = [], []
    for row in rows:
        identity = row.get('opId', row.get('op_id'))
        operation = row.get('mlirOpName', '')
        reason = None
        if type(identity) is not int or not 0 < identity <= 0x7fffffff:
            reason = 'not_a_device_observer_id'
        elif operation == 'arith.constant' or operation.startswith(('scf.', 'cf.', 'func.', 'flagtree_debug.')):
            reason = 'control_container_or_nonobservable_operation'
        elif '.call' in operation or operation.endswith(('return', 'yield')):
            reason = 'call_or_terminator'
        elif not operation:
            reason = 'missing_compiler_operation'
        item = dict(row, automatic_eligible=reason is None,
                    exclusion_reason=reason, selected=False)
        inventory.append(item)
        if reason is None:
            eligible.append(item)
    if not eligible:
        raise ValueError('Automatic observation found no instrumentable internal operations; compiler inventory retained in metadata')
    # Round-robin source classes, then spread within each class. This gives
    # memory, compute and aggregate regions representation without kernel names.
    buckets = {}
    for item in eligible:
        op = item['mlirOpName']
        category = ('memory' if any(part in op for part in ('load', 'store', 'atomic', 'copy'))
                    else 'aggregate' if any(part in op for part in ('reduce', 'scan', 'dot'))
                    else 'compute')
        buckets.setdefault(category, []).append(item)
    chosen = []
    order = ('memory', 'aggregate', 'compute')
    while len(chosen) < min(max_sites, len(eligible)):
        for category in order:
            bucket = buckets.get(category, [])
            if bucket and len(chosen) < max_sites:
                # Take alternate ends to avoid selecting only an address prefix.
                item = bucket.pop(0 if len(chosen) % 2 == 0 else -1)
                item['selected'] = True
                item['selection_reason'] = 'bounded_class_round_robin'
                chosen.append(item)
    return {'schema_version': 1, 'policy': 'bounded_class_round_robin',
            'max_sites': max_sites, 'candidate_count': len(eligible),
            'selected_sites': [item.get('opId', item.get('op_id')) for item in chosen],
            'inventory': inventory}
