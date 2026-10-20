"""Finite selected-reader paths within an actual indexed natural loop.

This proves bracket placement in actor LLVM, not a source trip count, dynamic
iteration IDs or final native scheduling. Unknown control paths are retained.
"""


class _Guards:

    def __init__(self, index):
        self.index = index
        self.cache = {}
        self.nodes = [('constant', False), ('constant', True)]
        self.interned = {}
        if not hasattr(index, '_loop_unstable_values'):
            users, unstable = {}, set()
            for instruction in index.instructions.values():
                if instruction['opcode'] == 'freeze':
                    continue
                for operand in instruction['operands']:
                    index.charge()
                    users.setdefault(operand['id'],
                                     []).append(instruction['id'])
                    if operand.get('constant_status') == 'undefined_or_poison':
                        unstable.add(operand['id'])
            pending = list(unstable)
            while pending:
                key = pending.pop()
                for user in users.get(key, ()):
                    index.charge()
                    if user not in unstable:
                        unstable.add(user)
                        pending.append(user)
            index._loop_unstable_values = frozenset(unstable)

    def intern(self, key):
        self.index.charge()
        if key not in self.interned:
            self.interned[key] = len(self.nodes)
            self.nodes.append(key)
        return self.interned[key]

    def key(self, value, depth=0):
        self.index.charge()
        if depth > 64:
            raise ValueError('Loop guard depth exceeded')
        if value in self.index._loop_unstable_values:
            raise ValueError(
                'Loop guard depends on explicit undefined/poison data')
        literal = self.index.literal(value)
        if literal and literal[0] == 1:
            return int(bool(literal[1]))
        if value in self.cache:
            return self.cache[value]
        instruction = self.index.instructions.get(value, {})
        operands = instruction.get('operands', [])
        opcode = instruction.get('opcode')
        result = None
        if opcode in ('and', 'or', 'xor'
                      ) and len(operands) == 2 and instruction['type'].get(
                          'integer_bits') == 1:
            left, right = sorted(
                self.key(o['id'], depth + 1) for o in operands)
            if left == right:
                result = 0 if opcode == 'xor' else left
            elif opcode == 'and':
                result = 0 if left == 0 else right if left == 1 else None
            elif opcode == 'or':
                result = right if left == 0 else 1 if left == 1 else None
            elif left == 0:
                result = right
            if result is None:
                result = self.intern((opcode, left, right))
        elif opcode == 'icmp' and len(operands) == 2:
            # Exact SSA operands or LLVM-uniqued constants only. Do not infer
            # equivalence of reloaded values or solve arbitrary expressions.
            values = [o['id'] for o in operands]
            if instruction['predicate'] in ('eq', 'ne'):
                values.sort()
            result = self.intern(('icmp', instruction['predicate'], *values))
        if result is None:
            result = self.intern(('opaque_ssa', value))
        self.cache[value] = result
        return result

    def evaluate(self, key, facts, depth=0):
        self.index.charge()
        if depth > 64:
            raise ValueError('Loop guard evaluation depth exceeded')
        if key < 2:
            return bool(key)
        if key in facts:
            return facts[key]
        node = self.nodes[key]
        if node[0] not in ('and', 'or', 'xor'):
            return None
        left, right = [self.evaluate(k, facts, depth + 1) for k in node[1:]]
        if node[0] == 'and':
            return False if left is False or right is False else True if left is True and right is True else None
        if node[0] == 'or':
            return True if left is True or right is True else False if left is False and right is False else None
        return left != right if left is not None and right is not None else None


def selected_loop_bracket(index, function, *, begin_id, end_id, context):
    result = dict(status='unverified',
                  source_iteration_ids_verified=False,
                  trip_count_verified=False,
                  native_schedule_qualified=False)
    try:
        if context['status'] != 'indexed_natural_loop_context':
            raise ValueError('Endpoints have no common indexed natural loop')
        loops = [
            loop for loop in function['loops']
            if loop['header'] == context['header_block_id']
        ]
        if len(loops) != 1:
            raise ValueError('Ambiguous indexed loop header')
        loop = loops[0]
        for _ in loop['blocks']:
            index.charge()
        allowed = set(loop['blocks'])
        predecessors = {}
        for block in function['blocks']:
            for successor in block['successors']:
                index.charge()
                predecessors.setdefault(successor, set()).add(block['id'])
        guards, facts, witnesses = _Guards(index), {}, []
        current = index.block[begin_id]
        visited = set()
        # A single-predecessor chain establishes facts necessarily true for
        # every execution reaching this actual start clock. Multiple incoming
        # paths never contribute a guessed selection fact.
        while current not in visited:
            index.charge()
            visited.add(current)
            incoming = predecessors.get(current, set())
            if len(incoming) != 1:
                break
            parent = index.blocks[next(iter(incoming))]
            if parent['id'] not in allowed or (parent['id'] in loop['latches']
                                               and current == loop['header']):
                break
            terminator = parent['instructions'][-1]
            successors = parent['successors']
            if terminator['opcode'] == 'br' and len(successors) == 2:
                if successors[0] != successors[1]:
                    predicate = terminator['operands'][0]['id']
                    facts[guards.key(predicate)] = successors[0] == current
                    witnesses.append(
                        dict(block_id=parent['id'],
                             predicate_id=predicate,
                             taken_successor=current))
                break
            if terminator['opcode'] != 'br' or len(successors) != 1:
                break
            current = parent['id']
        next_instruction = {}
        for block in function['blocks']:
            for left, right in zip(block['instructions'],
                                   block['instructions'][1:]):
                index.charge()
                next_instruction[left['id']] = right['id']
        colors, stack, count = {}, [(begin_id, False)], 0
        while stack:
            index.charge()
            key, closing = stack.pop()
            if key == end_id:
                continue
            if closing:
                colors[key] = 2
                continue
            if colors.get(key) == 2:
                continue
            if colors.get(key) == 1:
                raise ValueError('Selected bracket can cycle before its end')
            colors[key] = 1
            count += 1
            stack.append((key, True))
            block_id = index.block[key]
            if block_id not in allowed:
                raise ValueError('Selected bracket exits its loop before end')
            if key in next_instruction:
                targets = [next_instruction[key]]
            else:
                block = index.blocks[block_id]
                instruction = index.instructions[key]
                successors = block['successors']
                if instruction['opcode'] != 'br' or len(successors) not in (1,
                                                                            2):
                    raise ValueError(
                        'Unsupported loop endpoint control transfer')
                if len(successors) == 2:
                    value = guards.evaluate(
                        guards.key(instruction['operands'][0]['id']), facts)
                    if value is not None:
                        successors = [successors[0 if value else 1]]
                targets = []
                for successor in successors:
                    if block_id in loop['latches'] and successor == loop[
                            'header']:
                        raise ValueError(
                            'Selected bracket crosses a backedge before end')
                    if successor not in allowed:
                        raise ValueError(
                            'Selected bracket exits its loop before end')
                    targets.append(
                        index.blocks[successor]['instructions'][0]['id'])
            stack.extend((target, False) for target in targets)
        result.update(status='selected_llvm_bracket_within_iteration',
                      header_block_id=loop['header'],
                      latch_block_ids=loop['latches'],
                      exit_block_ids=loop['exits'],
                      begin_id=begin_id,
                      end_id=end_id,
                      selection_guard_witnesses=witnesses,
                      checked_path_nodes=count,
                      loop_backedge_or_exit_before_end=False)
    except (ValueError, KeyError, TypeError) as error:
        result['reason'] = str(error)
    return result
