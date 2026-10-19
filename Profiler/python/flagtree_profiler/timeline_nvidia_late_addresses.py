"""Native late-recorder address arithmetic relative to its published header.

Checks both address words, native carry/shift pairs and the actual record-count
register. Header allocation/program/thread origins are a separate obligation.
No temporal qualification follows from this structural arithmetic witness.
"""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from .timeline_nvidia_control import _bound_functions, _compact, _need, _registers
from .timeline_nvidia_late_values import _predecessors, _destinations, _predicate
from .timeline_nvidia_late_payloads import _Words, _Arena, MAX_STATES
from .timeline_nvidia_late_records import derive_record_fields, _native_store
from .timeline_nvidia_late_boundaries import _native_lines, _straight_path
from .timeline_nvidia_machine import _lex

MODEL = 'nvidia.late.header_relative_record_addresses.v1'
MASK64 = (1 << 64) - 1


class _ReachingWords(_Words):
    """All-path, function-scoped leaves; never merge separate definitions.

    Unlike payload epochs, invariant header inputs may cross a loop edge. The
    visited worklist is finite, but two different reaching writes still reject.
    Cyclic expressions are rejected by the inherited value resolver.
    """

    def __init__(self, body, graph):
        self.body, self.graph = body, graph
        self.cut = min(graph)
        self.arena, self.cache, self.active, self.def_cache = _Arena(
        ), {}, set(), {}

    def definitions(self, pc, register, pre=False):
        key = pc, register
        if key in self.def_cache:
            return self.def_cache[key]
        work, visited, definitions = [pc], set(), set()
        while work:
            at = work.pop()
            if at in visited:
                continue
            visited.add(at)
            _need(
                len(visited) <= MAX_STATES,
                'Address definition budget exceeded')
            parents = self.graph[at]
            if not parents:
                definitions.add(('entry', at, register))
            for parent in parents:
                row = self.body[parent]
                active = _predicate(row.get('predicate'))
                if active is not False and register in _destinations(row):
                    definitions.add(('definition', parent, register))
                    if active is True:
                        continue
                work.append(parent)
        _need(definitions, 'Address input has no reaching definition')
        _need(
            len(self.def_cache) < MAX_STATES,
            'Address definition cache exceeded')
        self.def_cache[key] = definitions
        return definitions


class _Wide:
    """Bounded 64-bit address DAG; no implicit truncation to a low word."""

    def __init__(self, body, graph, *, counter=None):
        self.body, self.graph = body, graph
        self.words = _ReachingWords(body, graph)
        self.counter = counter
        self.nodes, self.cache, self.active = {}, {}, set()
        self.lea_witnesses = {}

    def node(self, kind, *args):
        data = (kind, *args)
        key = hashlib.sha256(json.dumps(
            data, separators=(',', ':')).encode()).hexdigest()
        _need(
            len(self.nodes) < MAX_STATES or key in self.nodes,
            'Wide address expression budget exceeded')
        self.nodes[key] = data
        return key

    def add(self, *values):
        terms, constant = [], 0
        for value in values:
            children = self.nodes[value][1:] if type(
                value) is str and self.nodes.get(value,
                                                 (None, ))[0] == 'add64' else (
                                                     value, )
            for child in children:
                if type(child) is int:
                    constant = (constant + child) & MASK64
                else:
                    terms.append(child)
        terms.sort()
        if constant:
            terms.append(constant)
        return 0 if not terms else terms[0] if len(terms) == 1 else self.node(
            'add64', *terms)

    def shift(self, value, shift):
        _need(
            type(shift) is int and 0 <= shift < 64,
            'Invalid native address shift')
        if type(value) is int:
            return (value << shift) & MASK64
        return value if not shift else self.node('shift64', value, shift)

    def contains_count(self, value):
        work, seen = [value], set()
        while work:
            at = work.pop()
            if type(at) is not str or at not in self.nodes or at in seen:
                continue
            seen.add(at)
            row = self.nodes[at]
            if row[0] == 'published_count_epoch':
                return True
            work.extend(row[1:])
        return False

    def operand(self, pc, value):
        value = value.removesuffix('.reuse')
        if value in ('RZ', 'URZ'):
            return 0
        if re.fullmatch(r'-?0x[0-9a-fA-F]+', value):
            literal = int(value, 16)
            _need(not 0x80000000 <= literal <= 0xffffffff,
                  'Ambiguous native wide address literal')
            return literal & MASK64
        _need(re.fullmatch(r'U?R\d+', value),
              'Unknown wide native address operand')
        return self.pair(pc, value)

    def _one_definition(self, pc, register):
        rows = self.words.definitions(pc, register)
        _need(
            len(rows) == 1, 'Wide address has ambiguous reaching definitions')
        kind, at, _ = next(iter(rows))
        _need(kind == 'definition',
              'Wide address reaches an uninitialized register')
        _need(
            _predicate(self.body[at].get('predicate')) is True,
            'Predicated wide address definition')
        return at

    def pair(self, pc, register):
        key = pc, register
        if key in self.cache:
            return self.cache[key]
        _need(key not in self.active and len(self.active) < 128,
              'Cyclic or oversized wide address expression')
        _need(len(self.cache) < MAX_STATES, 'Wide address cache exceeded')
        self.active.add(key)
        try:
            low, high = _registers(register, 2)
            lo, hi = self._one_definition(pc,
                                          low), self._one_definition(pc, high)
            row = self.body[lo]
            fields = _compact(row.get('operands', '')).split(',')
            if lo == hi and fields[0] == register:
                opcode = row['opcode']
                if opcode in ('MOV.64', 'UMOV.64'):
                    result = self.operand(lo, fields[1])
                elif opcode == 'IADD.64':
                    _need(len(fields) == 3, 'Unknown wide address addition')
                    result = self.add(*(self.operand(lo, f)
                                        for f in fields[1:]))
                elif opcode in ('LDC.64', 'LDCU.64'):
                    _need(
                        re.fullmatch(r'c\[0x[0-9a-fA-F]+\]\[0x[0-9a-fA-F]+\]',
                                     fields[1]),
                        'Unknown native constant-memory address input')
                    result = self.node('constant_memory_u64', fields[1])
                elif opcode in ('SEL.64', 'USEL.64'):
                    result = self.node('select64',
                                       self.words.boolean(fields[3], lo),
                                       self.operand(lo, fields[1]),
                                       self.operand(lo, fields[2]))
                else:
                    raise ValueError('Unknown native wide address writer: ' +
                                     opcode)
            elif row['opcode'] == 'LEA' and self.body[hi][
                    'opcode'] == 'LEA.HI.X':
                upper = _compact(self.body[hi].get('operands', '')).split(',')
                _need(
                    len(fields) == 5 and len(upper) == 6 and hi > lo,
                    'Unknown native paired address formation')
                dest, carry, index, base, amount = fields
                index, base = index.removesuffix('.reuse'), base.removesuffix(
                    '.reuse')
                _need(
                    dest == low and upper[0] == high
                    and upper[1].removesuffix('.reuse') == index and
                    upper[2].removesuffix('.reuse') == _registers(base, 2)[1]
                    and upper[3].removesuffix('.reuse') == _registers(
                        index, 2)[1] and upper[4] == amount
                    and upper[5] == carry,
                    'Native low/high address operands or carry disagree')
                _need(
                    re.fullmatch(r'U?P\d+', carry) is not None,
                    'Native address carry was discarded')
                _need(
                    low not in set(_registers(index, 2) + _registers(base, 2)),
                    'Low address output overwrites an input needed by the high word'
                )
                _straight_path(self.body, lo, hi)
                protected = set(
                    _registers(index, 2) + _registers(base, 2) + [carry])
                for at in range(lo + 16, hi, 16):
                    if _predicate(self.body[at].get('predicate')) is not False:
                        _need(
                            not protected.intersection(
                                _destinations(self.body[at])),
                            'Native address inputs or carry changed between words'
                        )
                # A counter seed applies only to this actual LEA input. Its
                # live count definitions are checked by the caller.
                count = self.node('published_count_epoch'
                                  ) if index == self.counter else self.pair(
                                      lo, index)
                result = self.add(self.pair(lo, base),
                                  self.shift(count, int(amount, 16)))
                self.lea_witnesses[lo] = dict(low_pc=lo,
                                              high_pc=hi,
                                              index=index,
                                              base=base,
                                              shift=int(amount, 16),
                                              counter=index == self.counter)
            else:
                # Split scalar words retain their exact reaching definitions.
                # Equal low words alone can never establish equal pointers.
                result = self.node('words64', self.words.value(pc, low),
                                   self.words.value(pc, high))
            self.cache[key] = result
            return result
        finally:
            self.active.remove(key)


def derive_record_addresses(*, machine_map, sass_lines, sass_json, ptx, plan):
    relative = derive_record_fields(machine_map=machine_map,
                                    sass_lines=sass_lines,
                                    sass_json=sass_json,
                                    ptx=ptx,
                                    plan=plan)
    _need(
        all(r['status'] == 'native_record_fields_checked'
            for r in relative['sites']), 'Native field layout is incomplete')
    functions = _bound_functions(machine_map, sass_lines, sass_json)
    annotations = _native_lines(sass_lines, functions)
    lines, _ = _lex(ptx.decode(), 'late-v1')
    stride = plan['actors'] * 8
    reports = []
    for function, body in functions.items():
        sites = [r for r in relative['sites'] if r['function'] == function]
        if not sites:
            continue
        # Source-to-object annotation makes header identification independent
        # of register names, instruction offsets and operator source names.
        candidates = []
        for n, token in enumerate(lines, 1):
            match = re.fullmatch(r'st\.global\.b64\[(%rd\d+)\],(%rd\d+);',
                                 token)
            if match and (function, n) in annotations:
                header = [
                    (i + 1, x) for i, x in enumerate(lines) if re.fullmatch(
                        r'st\.global\.b64\[' + re.escape(match[1]) + r'\+' +
                        str(2 * stride) + r'\],1179667508;', x) and (
                            function, i + 1) in annotations
                ]
                if len(header) == 1:
                    candidates.append((n, match[1], match[2], header[0]))
        _need(
            len(candidates) == 1,
            'Missing or ambiguous published count header')
        count_line, source_header, source_count, magic = candidates[0]
        native_count = _native_store(function, count_line, annotations, body)
        native_magic = _native_store(function, magic[0], annotations, body)
        _need(
            native_magic['address_register']
            == native_count['address_register']
            and native_magic['descriptor'] == native_count['descriptor']
            and native_magic['offset'] - native_count['offset'] == 2 * stride,
            'Native published header fields do not share a base')
        counter = native_count['value_register']
        _need(counter != 'RZ', 'Published count is not a native register pair')
        graph = _predecessors(body)
        wide = _Wide(body, graph, counter=counter)
        header_address = _published_header_address(wide, native_count)
        batches = defaultdict(list)
        for site in sites:
            batches[site['source_base']].append(site)
        batch_rows = []
        for source_base, members in batches.items():
            ordered = sorted(members,
                             key=lambda r: r['source_batch_record_index'])
            _need([r['source_batch_record_index']
                   for r in ordered] == list(range(len(ordered))),
                  'Native source batch record indices are incomplete')
            for site in ordered:
                tag = site['fields'][0]
                _need(tag['descriptor'] == native_count['descriptor'],
                      'Record descriptor differs from published header')
                _need(
                    wide.pair(tag['pc'], tag['descriptor']) == wide.pair(
                        native_count['pc'], native_count['descriptor']),
                    'Actual record descriptor value differs from published header'
                )
                address = wide.add(
                    wide.pair(tag['pc'], tag['address_register']),
                    tag['offset'])
                expected = wide.add(header_address,
                                    site['source_tag_byte_offset'])
                count_term = wide.shift(wide.node('published_count_epoch'),
                                        (4 * stride).bit_length() - 1)
                _need(
                    (4 * stride) & (4 * stride - 1) == 0,
                    'Native shift-address witness requires power-of-two actor stride'
                )
                if address == expected:
                    mode = 'initial_zero_count'
                elif address == wide.add(expected, count_term):
                    mode = 'published_counter_relative'
                else:
                    raise ValueError(
                        'Native record address differs from header/count formula at site '
                        + str(site['site_id']))
                site['address_mode'] = mode
            _need(
                len({r['address_mode']
                     for r in ordered}) == 1,
                'One source batch has mixed counter bases')
            first_tag = ordered[0]['fields'][0]
            low_pc = wide._one_definition(first_tag['pc'],
                                          first_tag['address_register'])
            high_pc = wide._one_definition(
                first_tag['pc'],
                _registers(first_tag['address_register'], 2)[1])
            batch_rows.append(
                dict(source_base=source_base,
                     mode=ordered[0]['address_mode'],
                     site_ids=[r['site_id'] for r in ordered],
                     count=len(ordered),
                     address_low_pc=low_pc,
                     address_high_pc=high_pc,
                     field_store_pcs=sorted(f['pc'] for r in ordered
                                            for f in r['fields'])))
        # Exact live count-write inventory: zero initialization, initial
        # batch assignment, and positive self-adds matching complete batches.
        count_uses = {native_count['pc']} | {
            witness['low_pc']
            for witness in wide.lea_witnesses.values() if witness['counter']
        }
        live_writes = _live_count_definitions(body, graph, counter, count_uses)
        writes = _count_write_inventory(body, counter, live_writes)
        _need(
            sum(r['mode'] == 'initialize' for r in writes) == 1,
            'Published count lacks unique zero initialization')
        expected = sorted((b['count'], 'initial_batch_count' if b['mode'] ==
                           'initial_zero_count' else 'append_batch_count')
                          for b in batch_rows)
        actual = sorted((r['value'], r['mode']) for r in writes
                        if r['mode'] != 'initialize')
        _need(expected == actual,
              'Native count updates differ from complete source batches')
        _check_batch_control(body, graph, counter, batch_rows, writes)
        reports.append(
            dict(function=function,
                 status='native_header_relative_record_addresses_checked',
                 header=native_count,
                 source_header=source_header,
                 source_count=source_count,
                 batches=batch_rows,
                 count_writes=writes,
                 address_lea_pairs=list(wide.lea_witnesses.values()),
                 expression_nodes=len(wide.nodes)))
    _need(reports, 'No native record address witnesses')
    return dict(model=MODEL,
                binary_id=machine_map['binary_id'],
                functions=reports,
                proof_scope=
                'header_relative_address_arithmetic_and_count_write_inventory',
                absolute_raw_slot_binding_verified=False,
                dynamic_count_execution_verified=True,
                time_flows_qualified=False,
                implementation_sha256=_rule_digests())


def _count_write_inventory(body, counter, live_writes):
    writes = []
    for pc in sorted(live_writes):
        row = body[pc]
        fields = _compact(row.get('operands', '')).split(',')
        _need(
            _predicate(row.get('predicate')) is True and fields[0] == counter,
            'Published count has a partial or predicated write')
        if row['opcode'] == 'MOV.64' and fields[1] in ('RZ', 'URZ'):
            value, mode = 0, 'initialize'
        elif row['opcode'] == 'MOV.64' and re.fullmatch(
                r'0x[0-9a-fA-F]+', fields[1]):
            value = int(fields[1], 16)
            mode = 'initialize' if value == 0 else 'initial_batch_count'
        elif row['opcode'] == 'IADD.64' and len(
                fields) == 3 and fields[1] == counter and re.fullmatch(
                    r'0x[0-9a-fA-F]+', fields[2]):
            value, mode = int(fields[2], 16), 'append_batch_count'
        else:
            raise ValueError('Unknown published native count write at ' +
                             hex(pc))
        writes.append(dict(pc=pc, mode=mode, value=value))
    return writes


def _live_count_definitions(body, graph, counter, uses):
    """Find definitions feeding count uses, including loop-carried self-adds.

    Physical registers can hold unrelated temporaries before or after their
    counter lifetime. Never identify a counter definition by register number
    alone. Both words and all reaching paths are inspected; partial/predicated
    writes remain in the result for the caller to reject.
    """
    words = _ReachingWords(body, graph)
    registers = _registers(counter, 2)
    work = list(uses)
    visited, definitions = set(), set()
    while work:
        at = work.pop()
        if at in visited:
            continue
        visited.add(at)
        _need(
            len(visited) <= MAX_STATES,
            'Native count lifetime budget exceeded')
        for register in registers:
            for kind, pc, _ in words.definitions(at, register):
                _need(kind == 'definition',
                      'Native count use is uninitialized')
                definitions.add(pc)
                row = body[pc]
                fields = _compact(row.get('operands', '')).split(',')
                if (row['opcode'] == 'IADD.64' and len(fields) == 3
                        and fields[0] == fields[1] == counter):
                    work.append(pc)
    _need(definitions, 'Native count has no live definitions')
    return definitions


def _published_header_address(wide, native_count):
    address = wide.add(
        wide.pair(native_count['pc'], native_count['address_register']),
        native_count['offset'])
    _need(not wide.contains_count(address),
          'Published header address depends on a mutable record-count epoch')
    return address


def _no_prior_recording(graph, start, forbidden):
    """A zero reset or fixed-base initial batch must precede any recording."""
    work, visited = list(graph[start]), set()
    while work:
        pc = work.pop()
        if pc in visited:
            continue
        visited.add(pc)
        _need(
            len(visited) <= MAX_STATES,
            'Initial native count path budget exceeded')
        _need(pc not in forbidden,
              'Initial native count/batch can overwrite earlier records')
        work.extend(graph[pc])


def _check_batch_control(body, graph, counter, batches, writes):
    """Each complete store batch and its one count update execute together.

    Addresses consume the old full-width count before the append. The actual
    update may precede the stores due to scheduling; a single-entry straight
    region still guarantees either all stores/update or none. No dynamic path
    is chosen based on observed tick values.
    """
    record_stores = {
        pc
        for batch in batches
        for pc in batch['field_store_pcs']
    }
    initial = [r for r in writes if r['mode'] == 'initialize']
    _need(len(initial) == 1, 'Missing unique native count initialization')
    count_updates = {r['pc'] for r in writes if r['mode'] != 'initialize'}
    _no_prior_recording(graph, initial[0]['pc'], record_stores | count_updates)
    unused = {r['pc']: r for r in writes if r['mode'] != 'initialize'}
    for batch in batches:
        wanted = 'initial_batch_count' if batch[
            'mode'] == 'initial_zero_count' else 'append_batch_count'
        candidates = []
        for pc, update in unused.items():
            if update['mode'] != wanted or update['value'] != batch['count']:
                continue
            points = batch['field_store_pcs'] + [
                batch['address_low_pc'], batch['address_high_pc'], pc
            ]
            try:
                _straight_path(body, min(points), max(points))
            except ValueError:
                continue
            candidates.append(pc)
        _need(
            len(candidates) == 1,
            'Record batch and count update are not one unambiguous straight native region'
        )
        update = unused.pop(candidates[0])
        if wanted == 'initial_batch_count':
            # The count register may have held an unrelated temporary before
            # this literal assignment. What matters for a fixed zero-based
            # batch is that it cannot overwrite earlier recorded events.
            start = min(batch['field_store_pcs'] + [
                batch['address_low_pc'], batch['address_high_pc'], update['pc']
            ])
            _no_prior_recording(graph, start, record_stores | count_updates)
        else:
            _need(batch['address_high_pc'] < update['pc'],
                  'Native batch address reads an already incremented count')
            for at in range(batch['address_low_pc'], update['pc'], 16):
                _need(
                    not set(_registers(counter, 2)).intersection(
                        _destinations(body[at])),
                    'Native count changed between batch address and append')
        batch['count_update_pc'] = update['pc']
        batch['stores_and_count_update_execute_together'] = True
    _need(not unused, 'Unassociated native record-count update')


def load_record_ordinal_bindings(directory, capture, proof):
    """Bind complete observed batches to checked native count/address updates.

    The numerical byte offsets are relative to the published actor header;
    proving that header's absolute launch allocation is explicitly separate.
    """
    from .timeline_store import read_artifact
    from .timeline_nvidia_late_raw import decode_late_raw
    owner = capture['owner']
    _need(
        proof.get('model') == MODEL
        and proof.get('binary_id') == owner['binary_id']
        and proof.get('dynamic_count_execution_verified') is True,
        'Record address proof belongs to another binary or unavailable pattern'
    )
    _need(
        len(proof['functions']) == 1,
        'Ambiguous dynamic native entry function')
    batches = proof['functions'][0]['batches']
    starters = {r['site_ids'][0]: i for i, r in enumerate(batches)}
    _need(
        len(starters) == len(batches), 'Ambiguous native source batch starts')
    raw = read_artifact(directory, capture['raw_file'])
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Record binding raw changed')
    plan, layout = owner['plan'], owner['layout']
    decoded = decode_late_raw(plan, raw, slots=layout['slots'])
    _need(decoded['complete'], 'Native ordinal binding needs complete raw')
    stride = plan['actors'] * 8
    rows = []
    for program in decoded['programs']:
        physical = next(slot for slot, logical in layout['slots']
                        if logical == program['program_id'])
        for actor in program['observers']:
            events, first = actor['events'], 0
            header_byte = physical * plan['segment_words'] * 8 + actor[
                'actor'] * 8
            while first < len(events):
                index = starters.get(events[first]['site_id'])
                _need(index is not None,
                      'Raw occurrence does not start a native recorder batch')
                batch = batches[index]
                sequence = events[first:first + batch['count']]
                _need([r['site_id'] for r in sequence] == batch['site_ids'],
                      'Raw record order differs from complete native batch')
                _need(batch['mode'] != 'initial_zero_count' or first == 0,
                      'Native zero-count batch appears after earlier records')
                for offset, event in enumerate(sequence):
                    expected = header_byte + (plan['header_words'] + 4 *
                                              (first + offset)) * stride
                    _need(
                        event['raw_tag_offset_bytes'] == expected and
                        event['raw_begin_offset_bytes'] == expected + stride
                        and event['raw_end_offset_bytes']
                        == expected + 2 * stride
                        and event['raw_payload_offset_bytes']
                        == expected + 3 * stride,
                        'Actual raw field spans disagree with native count/stride formula'
                    )
                rows.append([
                    program['program_id'], actor['actor'], first, index,
                    batch['count']
                ])
                first += batch['count']
    return dict(model='nvidia.late.native_record_ordinal_bindings.v1',
                status='native_batch_count_relative_raw_addresses_checked',
                identity={
                    key: owner[key]
                    for key in ('capture_id', 'invocation_id', 'binary_id')
                },
                raw_sha256=decoded['raw_sha256'],
                columns=[
                    'program', 'actor', 'first_ordinal', 'native_batch_index',
                    'record_count'
                ],
                rows=rows,
                relative_record_ordinal_binding_verified=True,
                absolute_raw_slot_binding_verified=False,
                time_flows_qualified=False)


def _rule_digests():
    from . import timeline_nvidia_control, timeline_nvidia_late_values, timeline_nvidia_late_payloads, timeline_nvidia_late_records, timeline_nvidia_late_boundaries, timeline_nvidia_late_control, timeline_nvidia_machine
    modules = (timeline_nvidia_control, timeline_nvidia_late_values,
               timeline_nvidia_late_payloads, timeline_nvidia_late_records,
               timeline_nvidia_late_boundaries, timeline_nvidia_late_control,
               timeline_nvidia_machine)
    paths = [Path(__file__), *(Path(module.__file__) for module in modules)]
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def inspect_record_addresses(**inputs):
    try:
        return derive_record_addresses(**inputs)
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        return dict(model=MODEL,
                    binary_id=inputs['machine_map'].get('binary_id'),
                    status='unverified_native_record_addresses_or_pattern',
                    functions=[],
                    reason=str(error),
                    implementation_sha256=_rule_digests(),
                    absolute_raw_slot_binding_verified=False,
                    dynamic_count_execution_verified=False,
                    time_flows_qualified=False)
