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

    for flagged in (False, True):
        computed = copy.deepcopy(changed)
        actor = next(f for f in computed['functions'] if f['name'] == function)
        target = next(b for b in actor['blocks']
                      if b['id'] == witness['block_id'])
        second = next(i for i in target['instructions'] if i['id'] == fresh)
        descriptor_operand = copy.deepcopy(second['operands'][0])
        definition = dict(id=fresh + 200,
                          opcode='add',
                          type=descriptor_operand['type'],
                          nsw=flagged,
                          nuw=False,
                          operands=[
                              descriptor_operand,
                              dict(id=fresh + 201,
                                   integer_bits=64,
                                   integer_hex='0',
                                   type=descriptor_operand['type'])
                          ])
        target['instructions'].insert(target['instructions'].index(second),
                                      definition)
        second['operands'][0] = dict(id=definition['id'],
                                     type=definition['type'])
        rejected(
            'duplicate_with_' + ('opaque' if flagged else 'computed') +
            '_descriptor', computed)

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

    # Linear SSA can represent an exponentially expanded expression DAG.
    # Reject by the predicted expanded size before repr/sorting expands it.
    changed, actor, block, fields = context()
    argument = next(a for a in actor['arguments']
                    if a['type'].get('integer_bits') == 64)
    previous = argument['id']
    chain = []
    for n in range(24):
        value = dict(id=previous, type=argument['type'])
        instruction = dict(
            id=fresh + 300 + n,
            opcode='add' if n % 2 == 0 else 'mul',
            operands=[copy.deepcopy(value),
                      copy.deepcopy(value)],
            type=argument['type'],
            nsw=False,
            nuw=False)
        chain.append(instruction)
        previous = instruction['id']
    gep = next(i for i in block['instructions']
               if i['id'] == fields[0]['operands'][1]['id'])
    block['instructions'][block['instructions'].
                          index(gep):block['instructions'].index(gep)] = chain
    gep['operands'][1] = dict(id=previous, type=argument['type'])
    try:
        rules.bind_record_endpoints(changed, **options)
    except rules._BudgetExceeded as error:
        if 'expanded expression' not in str(error):
            raise RuntimeError(
                'DAG expansion did not hit its early size budget') from error
        results.append(
            dict(name='shared_DAG_expansion', rejected=True,
                 reason=str(error)))
    else:
        raise RuntimeError('Exponentially expanded expression was not bounded')
    return results
