"""Semantic faults applied to an actual native-indexed actor record.

Called in a server Docker by the retained-actor test runner. The input is a
real verified graph, not a fabricated kernel or per-operator adapter.
"""
import copy


def check_negative_records(rules, graph, *, manifest, function,
                           trace_argument_index):
    options = dict(manifest=manifest,
                   function=function,
                   trace_argument_index=trace_argument_index)
    original = rules.bind_record_endpoints(graph, **options)
    witness = next(r for r in original['regions']
                   if r['status'] == 'llvm_tuple_endpoints_bound')
    sid = witness['site_id']

    def context():
        changed = copy.deepcopy(graph)
        actor = next(f for f in changed['functions'] if f['name'] == function)
        block = next(b for b in actor['blocks']
                     if b['id'] == witness['block_id'])
        fields = [
            next(i for i in block['instructions'] if i['id'] == key)
            for key in witness['store_ids']
        ]
        return changed, actor, block, fields

    results = []

    def rejected(name, changed):
        result = rules.bind_record_endpoints(changed, **options)
        row = next(r for r in result['regions'] if r['site_id'] == sid)
        if row['status'] != 'unverified':
            raise RuntimeError('Incorrect record accepted: ' + name)
        results.append(dict(name=name, rejected=True, reason=row['reason']))

    for name, destination, source in [('start_is_end', 2, 3),
                                      ('end_is_start', 3, 2),
                                      ('commit_is_descriptor', 7, 0)]:
        changed, _, _, fields = context()
        fields[destination]['operands'][0] = copy.deepcopy(
            fields[source]['operands'][0])
        rejected(name, changed)

    changed, _, block, fields = context()
    block['instructions'].remove(fields[5])
    rejected('missing_actor_word', changed)

    changed, actor, _, fields = context()
    other = next(
        a for n, a in enumerate(actor['arguments'])
        if n != trace_argument_index and a['type'].get('address_space') == 1)
    by_id = {i['id']: i for b in actor['blocks'] for i in b['instructions']}
    gep = by_id[fields[5]['operands'][1]['id']]
    gep['operands'][0] = copy.deepcopy(other)
    rejected('one_word_targets_other_pointer', changed)

    changed, _, _, fields = context()
    constant = copy.deepcopy(fields[0]['operands'][0])
    constant['id'] = max(i['id'] for f in changed['functions']
                         for b in f['blocks']
                         for i in b['instructions']) + 10000
    descriptor = int(constant['integer_hex'], 16)
    semantic = 1 if descriptor >> 32 != 1 else 2
    constant['integer_hex'] = format((semantic << 32) | sid, 'X')
    fields[0]['operands'][0] = constant
    rejected('wrong_semantic', changed)

    changed, _, block, fields = context()
    fresh = max(i['id'] for f in changed['functions'] for b in f['blocks']
                for i in b['instructions']) + 10000
    duplicates = copy.deepcopy(fields)
    for n, store in enumerate(duplicates):
        store['id'] = fresh + n
    # Additional stores use existing dominating definitions, inserted before
    # the terminator. This represents a second complete physical tuple.
    block['instructions'][-1:-1] = duplicates
    rejected('two_complete_tuples', changed)

    # Interrupt discovery only when the later duplicate descriptor is read:
    # the first complete tuple has already been processed. Exhaustion must
    # abort, rather than return that earlier candidate as uniquely checked.
    duplicate_constant = copy.deepcopy(duplicates[0]['operands'][0])
    duplicate_constant['id'] = fresh + 100
    duplicates[0]['operands'][0] = duplicate_constant
    old_literal = rules._Index.literal

    def interrupted(index, key):
        if key == duplicate_constant['id']:
            raise rules._BudgetExceeded('Injected discovery exhaustion')
        return old_literal(index, key)

    rules._Index.literal = interrupted
    try:
        try:
            rules.bind_record_endpoints(changed, **options)
        except rules._BudgetExceeded:
            results.append(
                dict(name='incomplete_uniqueness_scan', rejected=True))
        else:
            raise RuntimeError('Budget exhaustion returned partial uniqueness')
    finally:
        rules._Index.literal = old_literal
    return results
