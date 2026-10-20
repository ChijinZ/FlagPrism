"""Actual native CFG fixtures plus semantic boundary/tuple/loop negatives.

All fixtures are self-contained LLVM, not copied vendor IR. The native helper
constructs the typed index. These are CPU rule tests, not device correctness or
SDK/native-scheduling evidence. Run in a normal server Docker installation.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest


def fixture(loop=True):
    lines = [
        'module {', 'llvm.func @_ZN4tops12global_timerEv() -> i64',
        'llvm.func @flagprism_gcu_clock_identity_v1() -> i32',
        'llvm.func @anonymous(%selected: i1, %trip: i32, %ring: !llvm.ptr, %counter: !llvm.ptr, %X: !llvm.ptr) {'
    ]
    for number in sorted(
            set(range(40)) | {512, 0x7fffffff, 0x46504733, 0x46504743}):
        lines.append(f'%c{number} = llvm.mlir.constant({number} : i32) : i32')
    lines += [
        '%shift = llvm.mlir.constant(32 : i64) : i64',
        'llvm.br ^header(%c0 : i32)' if loop else 'llvm.br ^guard'
    ]
    if loop:
        lines += [
            '^header(%i: i32):', '%again = llvm.icmp "slt" %i, %trip : i32',
            'llvm.cond_br %again, ^guard, ^exit'
        ]
    lines += [
        '^guard:',
        'llvm.cond_br %selected, ^begin, ^body(%c0, %c0, %c0 : i32, i32, i32)',
        '^begin:',
        '%b = llvm.call @_ZN4tops12global_timerEv() : () -> i64 loc("__flagprism_gcu_clock_v1__":7:1)',
        '%bl = llvm.trunc %b : i64 to i32', '%bs = llvm.lshr %b, %shift : i64',
        '%bh = llvm.trunc %bs : i64 to i32',
        '%bi = llvm.call @flagprism_gcu_clock_identity_v1() : () -> i32 loc("__flagprism_gcu_clock_v1__":7:3)',
        'llvm.br ^body(%bl, %bh, %bi : i32, i32, i32)',
        '^body(%low: i32, %high: i32, %owner: i32):',
        '%x = llvm.load %X : !llvm.ptr -> f32 loc("fixture.py":1:12)',
        '%square = llvm.fmul %x, %x : f32 loc("fixture.py":1:20)',
        'llvm.store %square, %X : f32, !llvm.ptr loc("fixture.py":1:24)',
        'llvm.cond_br %selected, ^end, ^latch', '^end:',
        '%e = llvm.call @_ZN4tops12global_timerEv() : () -> i64 loc("__flagprism_gcu_clock_v1__":7:2)',
        '%el = llvm.trunc %e : i64 to i32', '%es = llvm.lshr %e, %shift : i64',
        '%eh = llvm.trunc %es : i64 to i32',
        '%ei = llvm.call @flagprism_gcu_clock_identity_v1() : () -> i32 loc("__flagprism_gcu_clock_v1__":7:4)',
        '%seq = llvm.load %counter : !llvm.ptr -> i32',
        '%nextseq = llvm.add %seq, %c1 : i32',
        '%saturated = llvm.icmp "eq" %seq, %c2147483647 : i32',
        '%updated = llvm.select %saturated, %seq, %nextseq : i1, i32',
        'llvm.store %updated, %counter : i32, !llvm.ptr',
        '%space = llvm.icmp "ult" %seq, %c512 : i32',
        'llvm.cond_br %space, ^record, ^latch', '^record:',
        '%slot = llvm.mul %seq, %c32 : i32'
    ]
    fields = {
        0: '%c1179666227',
        1: '%c7',
        2: '%seq',
        3: '%c5',
        4: '%low',
        5: '%high',
        6: '%el',
        7: '%eh',
        8: '%ei',
        18: '%owner',
        19: '%ei',
        31: '%c1179666243'
    }
    for word in range(32):
        lines += [
            f'%offset{word} = llvm.add %slot, %c{8 + word} : i32',
            f'%address{word} = llvm.getelementptr %ring[%offset{word}] : (!llvm.ptr, i32) -> !llvm.ptr, i32',
            f'llvm.store {fields.get(word, "%c0")}, %address{word} : i32, !llvm.ptr'
        ]
    lines += ['llvm.br ^latch', '^latch:']
    lines += [
        '%next = llvm.add %i, %c1 : i32', 'llvm.br ^header(%next : i32)'
    ] if loop else ['llvm.br ^exit']
    lines += ['^exit:', 'llvm.return', '}', '}']
    manifest = dict(capacity=512,
                    sites=[
                        dict(id=7,
                             kind=5,
                             operation='gcu.border',
                             location='loc("fixture.py":1:1)')
                    ])
    return '\n'.join(lines), manifest


def shared_fixture():
    text, manifest = fixture(False)
    text = text.replace('%selected: i1, %trip:',
                        '%selected: i1, %which: i1, %trip:')
    entry = text[:text.index('llvm.br ^guard')]
    body = text[text.index('^guard:'):text.index('^end:')]
    tail = text[text.index('^end:'):]
    local = {
        'b', 'bl', 'bs', 'bh', 'bi', 'low', 'high', 'owner', 'x', 'square'
    }
    variants = []
    for site in (7, 8):
        part = re.sub(
            r'%([A-Za-z][\w]*)', lambda m: '%' + m[1] +
            (str(site) if m[1] in local else ''), body)
        for label in ('guard', 'begin', 'body'):
            part = part.replace('^' + label, '^' + label + str(site))
        part = part.replace('"__flagprism_gcu_clock_v1__":7:',
                            f'"__flagprism_gcu_clock_v1__":{site}:')
        part = part.replace('"fixture.py":1:', f'"fixture.py":{site - 6}:')
        part = part.replace(
            '^end, ^latch',
            f'^end(%c{site}, %low{site}, %high{site}, %owner{site} : i32, i32, i32, i32), ^latch'
        )
        variants.append(part)
    tail = tail.replace(
        '^end:',
        '^end(%commonSite: i32, %commonLow: i32, %commonHigh: i32, %commonIdentity: i32):'
    )
    tail = re.sub(
        r'%(low|high|owner)\b', lambda m: {
            'low': '%commonLow',
            'high': '%commonHigh',
            'owner': '%commonIdentity'
        }[m[1]], tail)
    tail = tail.replace('llvm.store %c7, %address1 :',
                        'llvm.store %commonSite, %address1 :')
    manifest['sites'] = [
        dict(id=site,
             kind=5,
             operation='gcu.border',
             location=f'loc("fixture.py":{site - 6}:1)') for site in (7, 8)
    ]
    return entry + 'llvm.cond_br %which, ^guard7, ^guard8\n' + ''.join(
        variants) + tail, manifest


class BoundaryTests(unittest.TestCase):
    module = None
    tool = None
    output = None
    cache = {}

    @classmethod
    def indexed(cls, loop=True):
        if loop not in cls.cache:
            shared = loop in ('shared', 'legacy-shared')
            text, manifest = shared_fixture() if shared else fixture(loop)
            if loop == 'preheader-runtime':
                text = text.replace(
                    'llvm.br ^header(%c0 : i32)',
                    'llvm.br ^preheader\n^preheader:\n'
                    '%bound = llvm.add %trip, %c0 : i32\n'
                    'llvm.br ^header(%c0 : i32)')
                text = text.replace('%again = llvm.icmp "slt" %i, %trip',
                                    '%again = llvm.icmp "slt" %i, %bound')
            if loop in ('continued-runtime', 'nested-control-runtime',
                        'continued-constant'):
                text = text.replace('^latch', '^continuation')
                if loop in ('continued-runtime', 'continued-constant'):
                    continuation = '^continuation:\nllvm.br ^latch\n^latch:'
                else:
                    continuation = (
                        '^continuation:\nllvm.br ^inner(%c0 : i32)\n'
                        '^inner(%j: i32):\n'
                        '%more = llvm.icmp "slt" %j, %c2 : i32\n'
                        'llvm.cond_br %more, ^spin, ^latch\n'
                        '^spin:\n%jnext = llvm.add %j, %c1 : i32\n'
                        'llvm.br ^inner(%jnext : i32)\n^latch:')
                text = text.replace('^continuation:', continuation)
            if loop in ('constant', 'continued-constant', 'legacy-constant'):
                text = text.replace('%again = llvm.icmp "slt" %i, %trip',
                                    '%again = llvm.icmp "slt" %i, %c3')
            if isinstance(loop, str) and loop.startswith('legacy-'):
                text = re.sub(r' loc\("__flagprism_gcu_clock_v1__":\d+:\d+\)',
                              '', text)
                text = text.replace('loc("fixture.py":', 'loc("-":')
            name = str(loop) if isinstance(
                loop, str) else 'runtime' if loop else 'straight'
            source, target = cls.output / (name + '.mlir'), cls.output / (
                name + '.json')
            source.write_text(text)
            child = subprocess.run([
                str(cls.tool), '--execution-structure',
                str(source),
                str(target)
            ],
                                   capture_output=True,
                                   timeout=20)
            if child.returncode:
                raise RuntimeError(child.stderr.decode())
            cls.cache[loop] = json.loads(target.read_text()), manifest
        return copy.deepcopy(cls.cache[loop])

    def checked(self, report, manifest):
        return self.module.analyze_regions(report, manifest)['regions'][0]

    def positive(self):
        report, manifest = self.indexed()
        region = self.checked(report, manifest)
        self.assertEqual(region['status'], 'llvm_observer_boundary_checked',
                         region)
        self.assertEqual(region['loop']['status'],
                         'llvm_runtime_iteration_checked', region)
        return report, manifest, region

    def test_record_payload_pointer_cast_does_not_hide_effects_or_tuple_changes(
            self):
        text, manifest = fixture(False)
        extra = (
            '%converted = llvm.addrspacecast %X : !llvm.ptr to !llvm.ptr<3>\n'
            '%payload = llvm.ptrtoint %converted : !llvm.ptr<3> to i32\n')
        text = text.replace('%slot =', extra + '%slot =')
        text = text.replace('llvm.store %c0, %address12 :',
                            'llvm.store %payload, %address12 :')
        source = self.output / 'record-address-space-cast.mlir'
        target = source.with_suffix('.json')
        source.write_text(text)
        child = subprocess.run([
            str(self.tool), '--execution-structure',
            str(source),
            str(target)
        ],
                               capture_output=True,
                               timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        report = json.loads(target.read_text())
        region = self.checked(report, manifest)
        self.assertEqual(region['status'], 'llvm_observer_boundary_checked',
                         region)
        cast = next(row for block in report['blocks']
                    for row in block['operations']
                    if row['operation'] == 'llvm.addrspacecast')
        invalid = copy.deepcopy(report)
        badcast = next(row for block in invalid['blocks']
                       for row in block['operations']
                       if row['operation'] == 'llvm.addrspacecast')
        badcast['operands'] = [
            next(row['results'][0] for block in invalid['blocks']
                 for row in block['operations']
                 if row.get('integer_constant') == 0)
        ]
        self.assertIn('typed pointer conversion',
                      self.checked(invalid, manifest)['reason'])
        for operation in ('llvm.call', 'llvm.fadd'):
            invalid = copy.deepcopy(report)
            altered = next(row for block in invalid['blocks']
                           for row in block['operations']
                           if cast['results'] == row['results'])
            altered['operation'] = operation
            self.assertIn('Unknown effect',
                          self.checked(invalid, manifest)['reason'])
        field = region['paths'][0]['field_refs']['1']
        report['blocks'][field['block']]['operations'][
            field['operation']]['operands'][0] = next(
                row['results'][0] for block in report['blocks']
                for row in block['operations']
                if row.get('integer_constant') == 0)
        self.assertIn('tuple', self.checked(report, manifest)['reason'])

    def test_flagged_overflow_is_not_a_literal_iteration_bound(self):
        text, manifest = fixture(True)
        derived = (
            '%minimum = llvm.mlir.constant(-2147483648 : i32) : i32\n'
            '%another = llvm.mlir.constant(-2147483645 : i32) : i32\n'
            '%derived = llvm.add %minimum, %another overflow<nsw> : i32\n')
        text = text.replace('%shift =', derived + '%shift =')
        text = text.replace('%again = llvm.icmp "slt" %i, %trip',
                            '%again = llvm.icmp "slt" %i, %derived')
        source = self.output / 'overflow-trip.mlir'
        target = source.with_suffix('.json')
        source.write_text(text)
        child = subprocess.run([
            str(self.tool), '--execution-structure',
            str(source),
            str(target)
        ],
                               capture_output=True,
                               timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        result = self.checked(json.loads(target.read_text()), manifest)
        self.assertEqual(result['status'], 'llvm_observer_boundary_checked',
                         result)
        self.assertEqual(result['loop']['status'], 'unverified', result)
        self.assertIn('actual literal definition', result['loop']['reason'])

    def legacy_shared(self):
        report, manifest = self.indexed('legacy-shared')
        regions = self.module.analyze_regions(report, manifest)['regions']
        self.assertTrue(
            all(x['status'] == 'llvm_observer_boundary_checked'
                for x in regions), regions)
        return report, manifest, regions

    def test_legacy_record_dispatch_checks_id_kind_and_order(self):
        report, manifest, regions = self.legacy_shared()
        manifest['sites'].reverse()
        manifest['sites'].insert(
            0,
            dict(id=99,
                 kind=5,
                 operation='gcu.border',
                 location='loc("fixture.py":9:1)'))
        found = {
            x['site_id']: x
            for x in self.module.analyze_regions(report, manifest)['regions']
        }
        self.assertEqual(found[7]['status'], 'llvm_observer_boundary_checked')
        self.assertEqual(found[8]['status'], 'llvm_observer_boundary_checked')
        self.assertEqual(found[99]['status'], 'unverified')
        next(x for x in manifest['sites'] if x['id'] == 8)['kind'] = 1
        found = {
            x['site_id']: x
            for x in self.module.analyze_regions(report, manifest)['regions']
        }
        self.assertEqual(found[7]['status'], 'llvm_observer_boundary_checked')
        self.assertEqual(found[8]['status'], 'unverified')
        # An unknown physical ID cannot be routed by source text or ordinal.
        report, manifest, regions = self.legacy_shared()
        body = report['blocks'][regions[1]['paths'][0]['body_blocks']
                                [0]]['operations'][-1]
        body['successors'][0]['arguments'][0] = report['blocks'][
            report['entry_block']]['arguments'][2]
        body['operands'][1] = body['successors'][0]['arguments'][0]
        found = {
            x['site_id']: x
            for x in self.module.analyze_regions(report, manifest)['regions']
        }
        self.assertEqual(found[7]['status'], 'llvm_observer_boundary_checked')
        self.assertEqual(found[8]['status'], 'unverified')

    def test_unfinished_discovery_cannot_claim_a_unique_legacy_begin(self):
        report, manifest, regions = self.legacy_shared()
        body = report['blocks'][regions[1]['paths'][0]['body_blocks']
                                [0]]['operations'][-1]
        seven = next(row['results'][0] for block in report['blocks']
                     for row in block['operations']
                     if row.get('integer_constant') == 7)
        body['successors'][0]['arguments'][0] = seven
        body['operands'][1] = seven
        original = self.module._region
        calls = []

        def interrupt_second(index, *args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                index.work = 1000001
                raise ValueError(
                    'LLVM boundary analysis work budget exhausted')
            return original(index, *args, **kwargs)

        self.module._region = interrupt_second
        try:
            result = self.module.analyze_regions(report, manifest)['regions']
        finally:
            self.module._region = original
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(x['status'] == 'unverified' for x in result),
                        result)
        self.assertTrue(all('budget exhausted' in x['reason'] for x in result),
                        result)

    def test_two_begins_claiming_one_legacy_site_are_ambiguous(self):
        report, manifest, regions = self.legacy_shared()
        body = report['blocks'][regions[1]['paths'][0]['body_blocks']
                                [0]]['operations'][-1]
        seven = next(row['results'][0] for block in report['blocks']
                     for row in block['operations']
                     if row.get('integer_constant') == 7)
        body['successors'][0]['arguments'][0] = seven
        body['operands'][1] = seven
        result = self.module.analyze_regions(report, manifest)['regions']
        self.assertTrue(all(x['status'] == 'unverified' for x in result),
                        result)

    def test_one_begin_cannot_hide_an_inconsistent_selected_branch(self):
        for corrupt in (False, True):
            report, manifest, regions = self.legacy_shared()
            first, second = regions
            remove = {second['begin_block'], *second['selection_guards']}
            remove.update(b for b in second['paths'][0]['body_blocks']
                          if b != second['paths'][0]['end_block'])
            report['blocks'] = [
                b for b in report['blocks'] if b['id'] not in remove
            ]
            blocks = {b['id']: b for b in report['blocks']}
            entry = blocks[report['entry_block']]
            entry['operations'][-1].update(
                operation='llvm.br',
                operands=[],
                successors=[
                    dict(block=first['selection_guards'][0], arguments=[])
                ])
            body = blocks[first['paths'][0]['body_blocks']
                          [0]]['operations'][-1]
            left = copy.deepcopy(body['successors'][0])
            right = copy.deepcopy(left)
            constant = lambda n: next(row['results'][0]
                                      for block in report['blocks']
                                      for row in block['operations']
                                      if row.get('integer_constant') == n)
            right['arguments'][0] = constant(8)
            if corrupt:
                right['arguments'][1] = constant(0)
            which = entry['arguments'][1]
            body.update(
                operation='llvm.cond_br',
                operands=[which, *left['arguments'], *right['arguments']],
                successors=[left, right])
            index = self.module._Index(report)
            index.infer_legacy_phases()
            with self.assertRaisesRegex(
                    ValueError,
                    'tuple' if corrupt else 'different producer sites'):
                self.module._region(
                    index,
                    None,
                    first['begin_block'],
                    manifest['capacity'],
                    sites={x['id']: x
                           for x in manifest['sites']})
            result = self.module.analyze_regions(report, manifest)['regions']
            self.assertTrue(all(x['status'] == 'unverified' for x in result),
                            result)

    def test_constant_iteration_is_separate_from_runtime_input(self):
        for variant in ('constant', 'continued-constant', 'legacy-constant'):
            with self.subTest(variant=variant):
                report, manifest = self.indexed(variant)
                region = self.checked(report, manifest)
                self.assertEqual(region['status'],
                                 'llvm_observer_boundary_checked', region)
                loop = region['loop']
                self.assertEqual(loop['status'],
                                 'llvm_constant_iteration_checked', loop)
                self.assertEqual(loop['constant_trip_count'], 3)
                self.assertFalse(loop['runtime_input_qualified'])
                self.assertNotIn('runtime_trip_value', loop)
                self.assertFalse(loop['source_iteration_id_qualified'])

    def test_constant_trip_zero_negative_and_wrapping_are_not_qualified(self):
        for value in (0, 0x80000000, 0xffffffff):
            report, manifest = self.indexed('constant')
            region = self.checked(report, manifest)
            trip = region['loop']['constant_trip_value']
            definition = next(row for block in report['blocks']
                              for row in block['operations']
                              if trip in row['results'])
            definition['integer_constant'] = value
            result = self.checked(report, manifest)
            self.assertEqual(result['status'],
                             'llvm_observer_boundary_checked', result)
            self.assertEqual(result['loop']['status'], 'unverified', result)
            self.assertIn('positive and non-wrapping',
                          result['loop']['reason'])

    def test_constant_iteration_still_rejects_wrong_step_and_reset(self):
        for mutation in ('step', 'reset'):
            report, manifest = self.indexed('constant')
            region = self.checked(report, manifest)
            loop = region['loop']
            literal = lambda n: next(row['results'][0]
                                     for block in report['blocks']
                                     for row in block['operations']
                                     if row.get('integer_constant') == n)
            if mutation == 'step':
                row = report['blocks'][loop['latch']]['operations'][0]
                self.assertEqual(row['operation'], 'llvm.add')
                row['operands'][1] = literal(2)
            else:
                report['blocks'][loop['exit_block']]['operations'][-1].update(
                    operation='llvm.br',
                    operands=[literal(0)],
                    successors=[
                        dict(block=loop['header'], arguments=[literal(0)])
                    ])
            result = self.checked(report, manifest)
            self.assertEqual(result['loop']['status'], 'unverified', result)

    def test_unmarked_typed_calls_recover_fresh_runtime_regions(self):
        report, manifest = self.indexed('legacy-runtime')
        self.assertFalse(
            any('clock_marker' in row for b in report['blocks']
                for row in b['operations']))
        original = copy.deepcopy(report)
        result = self.checked(report, manifest)
        self.assertEqual(result['status'], 'llvm_observer_boundary_checked',
                         result)
        self.assertEqual(result['loop']['status'],
                         'llvm_runtime_iteration_checked')
        self.assertEqual(result['clock_binding'],
                         'typed_timer_identity_call_roles')
        self.assertEqual(report, original)
        field = result['paths'][0]['field_refs']['1']
        zero = next(o['results'][0] for b in report['blocks']
                    for o in b['operations'] if o.get('integer_constant') == 0)
        report['blocks'][field['block']]['operations'][
            field['operation']]['operands'][0] = zero
        self.assertEqual(
            self.checked(report, manifest)['status'], 'unverified')

    def test_unmarked_body_does_not_invent_unknown_source_origin(self):
        report, manifest = self.indexed('legacy-runtime')
        manifest['sites'][0]['location'] = 'loc(unknown)'
        self.assertEqual(
            self.checked(report, manifest)['status'], 'unverified')

    def test_unmarked_source_origin_cannot_be_a_parser_placeholder(self):
        for location in ('loc("-":1:1)', 'loc("":1:1)',
                         'loc("fixture.py":0:1)'):
            with self.subTest(location=location):
                report, manifest = self.indexed('legacy-runtime')
                manifest['sites'][0]['location'] = location
                self.assertEqual(
                    self.checked(report, manifest)['status'], 'unverified')

    def test_unmarked_barrier_or_getter_is_not_a_fusion_compute_body(self):
        for callee in ('tops_syncthreads', 'tops_get_thread_idx'):
            with self.subTest(callee=callee):
                report, manifest = self.indexed('legacy-runtime')
                region = self.checked(report, manifest)
                self.assertEqual(region['status'],
                                 'llvm_observer_boundary_checked')
                body = []
                for ref in region['paths'][0]['body_refs']:
                    row = report['blocks'][ref['block']]['operations'][
                        ref['operation']]
                    row['operation'] = 'llvm.call'
                    row['callee'] = callee
                    body.append((ref['block'], ref['operation'], row))
                # Check the intended failure directly, so a record/count
                # protocol failure cannot make this body-family test pass.
                with self.assertRaisesRegex(ValueError, 'typed compute body'):
                    self.module._body_family(manifest['sites'][0],
                                             body,
                                             legacy=True)
                self.assertEqual(
                    self.checked(report, manifest)['status'], 'unverified')

    def test_unmarked_shared_end_uses_forwarded_site_tuple(self):
        report, manifest = self.indexed('legacy-shared')
        regions = self.module.analyze_regions(report, manifest)['regions']
        self.assertEqual(len(regions), 2)
        self.assertTrue(
            all(x['status'] == 'llvm_observer_boundary_checked'
                for x in regions), regions)
        self.assertEqual(regions[0]['paths'][0]['end_block'],
                         regions[1]['paths'][0]['end_block'])

    def test_runtime_loop_can_continue_through_a_separate_latch(self):
        for shape in ('continued-runtime', 'nested-control-runtime',
                      'preheader-runtime'):
            with self.subTest(shape=shape):
                report, manifest = self.indexed(shape)
                result = self.checked(report, manifest)
                self.assertEqual(result['status'],
                                 'llvm_observer_boundary_checked', result)
                self.assertEqual(result['loop']['status'],
                                 'llvm_runtime_iteration_checked', result)
                self.assertEqual(result['loop']['rule'],
                                 'single_header_latch_observer_state')
                self.assertFalse(result['loop']['termination_qualified'])
                header = report['blocks'][result['loop']
                                          ['header']]['operations'][-1]
                # Enter the body after the begin reader. Every record still
                # has valid local tuples, but iteration freshness must fail.
                begin = result['begin_block']
                edge = report['blocks'][begin]['operations'][-1]['successors'][
                    0]
                header['successors'][0] = copy.deepcopy(edge)
                header['operands'] = [header['operands'][0]
                                      ] + edge['arguments']
                changed = self.checked(report, manifest)
                self.assertNotEqual(
                    changed.get('loop', {}).get('status'),
                    'llvm_runtime_iteration_checked')

    def test_continuation_cycle_cannot_repeat_a_record_before_the_latch(self):
        report, manifest = self.indexed('continued-runtime')
        region = self.checked(report, manifest)
        join = report['blocks'][region['paths'][0]['join_block']]
        terminal = join['operations'][-1]
        original_edge = copy.deepcopy(terminal['successors'][0])
        condition = max(v for b in report['blocks'] for row in b['operations']
                        for v in row['results']) + 1
        entry = report['blocks'][report['entry_block']]
        entry['arguments'].append(condition)
        entry['argument_types'].append('i1')
        terminal.update(operation='llvm.cond_br',
                        operands=[condition],
                        successors=[
                            dict(block=region['paths'][0]['record_block'],
                                 arguments=[]), original_edge
                        ])
        result = self.checked(report, manifest)
        self.assertEqual(result['loop']['status'], 'unverified', result)

    def test_external_entry_does_not_hide_an_exit_reset_backedge(self):
        report, manifest = self.indexed('continued-runtime')
        region = self.checked(report, manifest)
        entry = report['blocks'][report['entry_block']]['operations'][-1]
        initial = copy.deepcopy(entry['successors'][0])
        entry.update(operation='llvm.cond_br',
                     operands=[region['selection_value']] +
                     initial['arguments'],
                     successors=[
                         initial,
                         dict(block=region['loop']['exit_block'], arguments=[])
                     ])
        exit_block = report['blocks'][region['loop']['exit_block']]
        exit_block['operations'][-1].update(operation='llvm.br',
                                            operands=list(
                                                initial['arguments']),
                                            successors=[initial])
        result = self.checked(report, manifest)
        self.assertEqual(result['loop']['status'], 'unverified', result)

    def test_original_members_resolve_an_unknown_border_without_changing_it(
            self):
        report, manifest = self.indexed('legacy-runtime')
        manifest['sites'][0]['location'] = 'loc(unknown)'
        self.assertEqual(
            self.checked(report, manifest)['status'], 'unverified')
        manifest['sites'][0]['source_membership'] = dict(
            schema_version=1,
            status='original_execution_members_indexed',
            members=[
                dict(operation_index=1,
                     operation='arith.mulf',
                     source_op_id=17,
                     scope_id=1,
                     file='fixture.py',
                     line=1,
                     column=20)
            ],
            enclosing_controls=[])
        result = self.checked(report, manifest)
        self.assertEqual(result['status'], 'llvm_observer_boundary_checked',
                         result)
        self.assertEqual(result['source_membership']['source_op_ids'], [17])
        self.assertTrue(
            result['source_membership']['producer_source_identity_required'])
        self.assertEqual(manifest['sites'][0]['location'], 'loc(unknown)')

    def test_invalid_or_placeholder_original_members_do_not_create_origins(
            self):
        for member in (dict(operation_index=1,
                            source_op_id=17,
                            scope_id=1,
                            file='-',
                            line=1),
                       dict(operation_index=1,
                            source_op_id=True,
                            scope_id=1,
                            file='fixture.py',
                            line=1),
                       dict(operation_index=-1,
                            source_op_id=17,
                            scope_id=1,
                            file='fixture.py',
                            line=1)):
            with self.subTest(member=member):
                report, manifest = self.indexed('legacy-runtime')
                manifest['sites'][0]['location'] = 'loc(unknown)'
                manifest['sites'][0]['source_membership'] = dict(
                    schema_version=1,
                    status='original_execution_members_indexed',
                    members=[member])
                self.assertEqual(
                    self.checked(report, manifest)['status'], 'unverified')

    def test_fresh_tuple_and_runtime_iteration(self):
        _, _, region = self.positive()
        self.assertEqual(region['loop']['selected_paths'], 2)
        self.assertFalse(region['native_schedule_qualified'])
        self.assertFalse(region['source_exclusive_cost_qualified'])

    def test_straight_line_region_is_not_a_runtime_loop(self):
        report, manifest = self.indexed(False)
        region = self.checked(report, manifest)
        self.assertEqual(region['status'], 'llvm_observer_boundary_checked',
                         region)
        self.assertEqual(region['loop']['status'], 'no_enclosing_runtime_loop')

    def test_stale_and_crossed_record_fields(self):
        report, manifest, region = self.positive()
        zero = next(o['results'][0] for b in report['blocks']
                    for o in b['operations'] if o.get('integer_constant') == 0)
        refs = region['paths'][0]['field_refs']
        for word in ('1', '2', '4', '5', '6', '7', '8', '18', '19', '31'):
            with self.subTest(word=word):
                changed = copy.deepcopy(report)
                ref = refs[word]
                changed['blocks'][ref['block']]['operations'][
                    ref['operation']]['operands'][0] = zero
                result = self.checked(changed, manifest)
                self.assertEqual(result['status'], 'unverified', result)
                self.assertIn('tuple', result['reason'])

    def test_late_overwrite_is_not_hidden_by_a_valid_prefix(self):
        report, manifest, region = self.positive()
        rows = report['blocks'][region['paths'][0]
                                ['record_block']]['operations']
        rows.insert(
            -1,
            copy.deepcopy(
                next(o for o in rows if o['operation'] == 'llvm.store')))
        self.assertEqual(
            self.checked(report, manifest)['status'], 'unverified')

    def test_unknown_memory_effect_in_record_is_rejected(self):
        report, manifest, region = self.positive()
        rows = report['blocks'][region['paths'][0]
                                ['record_block']]['operations']
        rows.insert(
            -1,
            dict(operation='llvm.intr.memset',
                 operands=[],
                 results=[],
                 result_types=[],
                 successors=[]))
        self.assertIn('Unknown effect',
                      self.checked(report, manifest)['reason'])

    def test_capacity_must_match_the_actual_guard(self):
        report, manifest, _ = self.positive()
        manifest['capacity'] = 1024
        self.assertIn('capacity differs',
                      self.checked(report, manifest)['reason'])

    def test_body_guard_cannot_bypass_end(self):
        report, manifest, region = self.positive()
        rows = report['blocks'][region['paths'][0]['body_blocks']
                                [0]]['operations']
        condition = rows[-1]['operands'][0]
        # Replace the end guard's condition by the runtime trip comparison;
        # both paths are possible after entering this bracket.
        header = report['blocks'][region['loop']['header']]
        rows[-1]['operands'][0] = header['operations'][-1]['operands'][0]
        self.assertNotEqual(rows[-1]['operands'][0], condition)
        self.assertEqual(
            self.checked(report, manifest)['status'], 'unverified')

    def test_loop_cannot_reuse_the_old_induction(self):
        report, manifest, region = self.positive()
        latch = report['blocks'][region['loop']['latch']]['operations'][-1]
        induction = region['loop']['induction_value']
        latch['operands'][0] = induction
        latch['successors'][0]['arguments'][0] = induction
        result = self.checked(report, manifest)
        self.assertEqual(result['status'], 'llvm_observer_boundary_checked')
        self.assertEqual(result['loop']['status'], 'unverified')

    def test_unknown_source_is_not_guessed(self):
        report, manifest, _ = self.positive()
        manifest['sites'][0]['location'] = 'loc(unknown)'
        self.assertIn('No original source',
                      self.checked(report, manifest)['reason'])

    def test_record_count_cannot_reuse_the_previous_slot(self):
        report, manifest, region = self.positive()
        end = report['blocks'][region['paths'][0]['end_block']]['operations']
        store = next(o for o in end if o['operation'] == 'llvm.store')
        load = next(o for o in end if o['operation'] == 'llvm.load')
        store['operands'][0] = load['results'][0]
        self.assertIn('saturating protocol',
                      self.checked(report, manifest)['reason'])

    def test_count_load_cannot_be_reused_across_loop_iterations(self):
        report, manifest, region = self.positive()
        end = report['blocks'][region['paths'][0]['end_block']]['operations']
        load = next(o for o in end if o['operation'] == 'llvm.load')
        end.remove(load)
        report['blocks'][report['entry_block']]['operations'].insert(-1, load)
        self.assertIn('attempted-count load',
                      self.checked(report, manifest)['reason'])

    def test_shared_end_is_bound_by_each_incoming_tuple(self):
        report, manifest = self.indexed('shared')
        regions = self.module.analyze_regions(report, manifest)['regions']
        self.assertTrue(
            all(row['status'] == 'llvm_observer_boundary_checked'
                for row in regions), regions)
        self.assertEqual(regions[0]['paths'][0]['end_block'],
                         regions[1]['paths'][0]['end_block'])
        self.assertEqual(regions[0]['paths'][0]['record_block'],
                         regions[1]['paths'][0]['record_block'])

    def test_shared_end_rejects_one_incorrect_incoming_site(self):
        report, manifest = self.indexed('shared')
        seven = next(o['results'][0] for b in report['blocks']
                     for o in b['operations']
                     if o.get('integer_constant') == 7)
        regions = self.module.analyze_regions(report, manifest)['regions']
        body = report['blocks'][regions[1]['paths'][0]['body_blocks']
                                [0]]['operations'][-1]
        body['successors'][0]['arguments'][0] = seven
        body['operands'][1] = seven
        result = self.module.analyze_regions(report, manifest)['regions']
        self.assertEqual(result[0]['status'], 'llvm_observer_boundary_checked')
        self.assertEqual(result[1]['status'], 'unverified')

    def test_shared_end_debug_site_does_not_select_the_record_owner(self):
        report, manifest = self.indexed('shared')
        for block in report['blocks']:
            for row in block['operations']:
                if row.get('clock_marker', {}).get('column') in (2, 4):
                    row['clock_marker']['site'] = 8
        regions = self.module.analyze_regions(report, manifest)['regions']
        self.assertTrue(
            all(row['status'] == 'llvm_observer_boundary_checked'
                for row in regions), regions)

    def test_an_unselected_path_cannot_enter_the_begin_reader(self):
        report, manifest = self.indexed(False)
        region = self.checked(report, manifest)
        terminal = report['blocks'][report['entry_block']]['operations'][-1]
        terminal.update(operation='llvm.cond_br',
                        operands=[region['selection_value']],
                        successors=[
                            dict(block=region['selection_guards'][0],
                                 arguments=[]),
                            dict(block=region['begin_block'], arguments=[])
                        ])
        self.assertIn('unselected observer',
                      self.checked(report, manifest)['reason'])

    def test_loop_exit_cannot_reenter_the_latch(self):
        report, manifest, region = self.positive()
        header = report['blocks'][region['loop']['header']]['operations'][-1]
        header['successors'][1]['block'] = region['loop']['latch']
        result = self.checked(report, manifest)
        self.assertEqual(result['loop']['status'], 'unverified')
        self.assertIn('exit reenters', result['loop']['reason'])

    def test_undefined_boundary_value_cannot_cancel_to_a_constant(self):
        for operation in ('llvm.mlir.undef', 'llvm.mlir.poison'):
            with self.subTest(operation=operation):
                text, manifest = fixture(False)
                extra = ('%undefined = ' + operation + ' : i32\n'
                         '%cancelled = llvm.sub %undefined, %undefined : i32\n'
                         '%fabricated = llvm.add %cancelled, %c7 : i32\n')
                text = text.replace('%shift =', extra + '%shift =')
                text = text.replace('llvm.store %c7, %address1 :',
                                    'llvm.store %fabricated, %address1 :')
                source = self.output / (operation + '.mlir')
                target = source.with_suffix('.json')
                source.write_text(text)
                child = subprocess.run([
                    str(self.tool), '--execution-structure',
                    str(source),
                    str(target)
                ],
                                       capture_output=True,
                                       timeout=20)
                self.assertEqual(child.returncode, 0, child.stderr.decode())
                region = self.checked(json.loads(target.read_text()), manifest)
                self.assertEqual(region['status'], 'unverified', region)
                self.assertIn('Undefined or poison', region['reason'])

    def test_opaque_integer_cancellation_and_zero_scaling_are_not_proofs(self):
        value = self.module._atom(32, 'ssa:unknown')
        with self.assertRaisesRegex(ValueError, 'cancellation'):
            self.module._add(value, self.module._scale(value, -1))
        with self.assertRaisesRegex(ValueError, 'scaling'):
            self.module._scale(value, 0)

    def test_loop_exit_cannot_reset_the_header_induction(self):
        report, manifest, region = self.positive()
        zero = next(o['results'][0] for b in report['blocks']
                    for o in b['operations'] if o.get('integer_constant') == 0)
        exit_block = report['blocks'][region['loop']['exit_block']]
        exit_block['operations'][-1].update(
            operation='llvm.br',
            operands=[zero],
            successors=[
                dict(block=region['loop']['header'], arguments=[zero])
            ])
        result = self.checked(report, manifest)
        self.assertEqual(result['loop']['status'], 'unverified', result)
        self.assertIn('reset induction', result['loop']['reason'])

    def test_continuation_cannot_repeat_end_without_a_fresh_begin(self):
        report, manifest = self.indexed(False)
        region = self.checked(report, manifest)
        # An i1 argument may branch either way; no new native/SDK execution.
        condition = region['selection_value']
        latch = report['blocks'][region['paths'][0]['join_block']]
        latch['operations'][-1].update(
            operation='llvm.cond_br',
            operands=[condition],
            successors=[
                dict(block=region['paths'][0]['end_block'], arguments=[]),
                dict(block=latch['operations'][-1]['successors'][0]['block'],
                     arguments=[])
            ])
        result = self.checked(report, manifest)
        self.assertEqual(result['loop']['status'], 'unverified', result)
        self.assertIn('without a fresh begin', result['loop']['reason'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--module', type=Path, required=True)
    parser.add_argument('--tool', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args, rest = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        'gcu_boundary_rule_under_test', args.module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    BoundaryTests.module, BoundaryTests.tool, BoundaryTests.output = module, args.tool, args.output
    args.output.mkdir(parents=True)
    unittest.main(argv=[__file__, *rest])
