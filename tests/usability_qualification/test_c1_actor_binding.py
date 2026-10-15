"""CPU-only synthetic adversarial public bundles; never device/math evidence."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

import check_common_report_c1 as c
import check_dynamic_report_c1 as dynamic
import c1_actor_binding as binding
import c1_verifier_authorization as authorization


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(root, slot=2, actor_kind='AIV'):
    """Two internal positions, two same-binary calls and exact 2/5 visits."""
    source = b'def runtime_recurrence():\n    first = 1\n    second = 2\n'
    module_text, adapted_text = 'synthetic original module', 'synthetic adapted module'
    module, compile_id, function = sha(module_text.encode()), 'compile-synthetic', 'synthetic_entry'
    actor_id = f'late_llvm:{module}:{function}'
    runtime_binding = dict(schema_version=1, function=function, actor_kind=actor_kind,
        module_sha256=module, compile_id=compile_id, layout='actor_header4_record8_v1',
        segment_count=3, segment_words=4 + 16 * 8, record_actor_word=5,
        admissible_slots=[0] if actor_kind == 'AIC' else [1, 2],
        expression={'kind': 'constant_i64', 'value': 0} if actor_kind == 'AIC' else
        {'kind': 'add_i64', 'call': 'llvm.hivm.GET.SUBBLOCKID', 'constant': 1},
        value_use='same_emitted_i64_for_segment_offset_and_record_word5',
        basis='actual_emitted_logger_actor_value')
    item = dict(site_id=7, selected=True, selection_reason='synthetic_selected',
                public_semantic='operation_checkpoint', operation='mul', source_file='/app/kernels.py', line=2)
    control = dict(site_id=8, selected=True, selection_reason='all_requested_original_loop_headers',
                   public_semantic='control_checkpoint', operation='loop_header_occurrence', source_file='/app/kernels.py', line=3)
    operation_plan = dict(candidate_count=1, selected_count=1, max_sites=8,
                          policy='synthetic_finite_policy', inventory=[item], plan_kind='operation',
                          budget_scope='source_operation_candidates_only', control_sites_included=False)
    control_plan = dict(candidate_count=1, selected_count=1, max_sites=None,
                        policy='all_requested_original_control_sites', inventory=[control], plan_kind='control',
                        budget_scope='existing_primitives_and_original_loop_headers',
                        operation_max_sites_applies=False, record_capacity_per_actor=16)
    metadata = dict(module_sha256=module, compile_id=compile_id,
                    actors=[dict(function=function, actor_kind=actor_kind)], runtime_actor_binding=runtime_binding,
                    operation_plan=operation_plan, control_plan=control_plan, dynamic_sites=[item, control])
    manifest_text = json.dumps(metadata)
    artifact = dict(sha256=module, llir=module_text, manifest_text=manifest_text,
                    manifest_sha256=sha(manifest_text.encode()), metadata=metadata,
                    adapted=dict(sha256=sha(adapted_text.encode()), llir=adapted_text))
    proof = dict(status='verified_compiler_emission_manifest', manifest_sha256=artifact['manifest_sha256'],
                 original_module_sha256=module, adapted_module_sha256=artifact['adapted']['sha256'],
                 selection_membership='selected_dynamic_site_in_exact_module_plan', observed_actor_slot=slot,
                 runtime_slot_status='verified_against_raw_record_and_segment')
    actor = dict(id=actor_id, function=function, kind=actor_kind, module_sha256=module,
                 compile_id=compile_id, runtime_actor_binding=runtime_binding, binding_proof=proof)
    plans = [dict(binary_id='binary-a', module_sha256=module, compile_id=compile_id,
                  plan_kind=kind, actor=None, compiler_actors=[dict(identity=actor_id, function=function,
                  actor_kind=actor_kind, runtime_actor_binding=runtime_binding)], plan=plan)
             for kind, plan in [('operation', operation_plan), ('control', control_plan)]]
    captures, observations, records, launches = [], [], [], []
    for call, count in [('launch-a', 2), ('launch-b', 5)]:
        cid = 'capture-' + call
        launches.append(dict(id=call, binary_id='binary-a'))
        raw_records = []
        for n in range(count):
            for selected in [item, control]:
                ordinal = len(raw_records)
                raw_record = [(binding.SEMANTIC_KIND[selected['public_semantic']] << 32) | selected['site_id'],
                              ordinal, ordinal + 100, ordinal + 100, 0, slot, 2**64-1, 2**64-1]
                raw_records.append(raw_record)
                observation = dict(id=f'{cid}-{ordinal}', capture_id=cid, invocation_id=call,
                    site=selected['site_id'], semantic=selected['public_semantic'], program=0,
                    occurrence=ordinal, actor_slot=slot, start_tick=ordinal+100, end_tick=ordinal+100,
                    original_record=raw_record, compiler_actor_status='verified_against_raw_record_and_segment',
                    compiler_site={**selected, 'actor_slot': slot, 'compiler_actor': actor},
                    association_evidence={'binary_id': 'binary-a'})
                observations.append(observation)
                records.append({key: value for key, value in dict(**observation, binary_id='binary-a',
                    actor=slot, compiler_actor=actor, iteration=None,
                    source_locations=[dict(file='/app/kernels.py', line=selected['line'], column=1)],
                    operation=selected['operation'], association_status='verified', source_status='located',
                    native_event_ids=[], clock=dict(domain='synthetic.counter', scope='actor_local',
                    alignment='instance_local', tick_ns=None), duration_ticks=0, duration_ns=None,
                    relative_start_ns=None, unit='ticks', truncated=False, sampling=None).items()})
        words = [0] * (3 * runtime_binding['segment_words'])
        offset = slot * runtime_binding['segment_words']
        words[offset:offset+4] = [1, len(raw_records), len(raw_records), 0]
        for n, raw_record in enumerate(raw_records):
            words[offset+4+n*8:offset+12+n*8] = raw_record
        raw = struct.pack('<' + 'Q' * len(words), *words)
        actor_rows = [dict(actor_slot=s, state='complete' if s == slot else 'no_records',
                           attempted=len(raw_records) if s == slot else 0,
                           committed=len(raw_records) if s == slot else 0, dropped=0,
                           execution_status='unknown', binding_status='verified_by_committed_records' if s == slot else 'unknown_no_records',
                           compiler_actors=[actor_id] if s == slot else []) for s in range(3)]
        captures.append(dict(capture_id=cid, capture_status='decoded', decode_error=None,
                            counter_saturated=False, actors=actor_rows, dropped=0,
                            record_layout='ascend_actor_dynamic_v1', raw_encoding='base64_ascend_actor_dynamic_v1',
                            raw_base64=base64.b64encode(raw).decode(), raw_sha256=sha(raw)))
    binary = dict(id='binary-a', identity='compiler_cache_hash', binary_sha256='b'*64,
                  source=dict(path='/app/kernels.py', file_sha256=sha(source), file_snapshot_file='ai/source.py',
                              sha256=sha(source), text_file='ai/source.py'),
                  compiler_metadata=dict(flagprism_ascend_handoff=dict(compile_id=compile_id, artifacts=[artifact])),
                  compiler_artifact_files=dict(llir=dict(file='raw/compiler.ll', sha256=module,
                                                        bytes=len(module_text.encode()))))
    call = dict(compiled_kernel_hash='binary-a', atol=0, rtol=0, input_unchanged=True, canaries=True)
    receipt = dict(case='runtime_recurrence', shape_index=0, config_index=0,
                   shape=[3], config={'x': 1}, grid=[1], input_sha256={'x': 'f'*64},
                   calls=[dict(call, runtime_steps=2), dict(call, runtime_steps=5)])
    baseline = dict(receipt, cold_timeout_s=120)
    cohort = dict(source_sha256={'kernels.py': sha(source)}, cases=[],
                  backend_evidence={'ascend': dict(runtime_probe=[baseline], common_combinations=[])})
    documents = {'ai/fine_grained.json': dict(schema_version=1, status='dynamic_records_available', records=records,
                                              captures=captures, rejected=[], limits=[]),
                 'ai/observations.json': dict(schema_version=1, observations=observations, captures=captures),
                 'ai/observation_plan.json': dict(schema_version=1, plans=plans, capture_evidence=captures),
                 'ai/binaries.json': [binary], 'ai/launches.json': launches,
                 'ai/execution.json': {},
                 'ai/export_timing.json': dict(schema_version=1, clock='host.monotonic', unit='seconds',
                    complete_finalize_and_export=True, phases=dict(collector_finalize_s=1, bundle_materialization_s=1),
                    export_wall_s=2, scope='collector_finalize_then_bundle_export'),
                 'ai/deadlines.json': dict(schema_version=1, enforced=True, supervisor_worker_launches=1,
                    limits_seconds=dict(startup=120, compile=120, export=60), application_runtime_limit=None)}
    bundle = root / 'bundle'
    for path, value in documents.items():
        target = bundle / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))
    (bundle / 'ai/source.py').write_bytes(source)
    (bundle / 'raw').mkdir()
    (bundle / 'raw/compiler.ll').write_text(module_text)
    (bundle / 'report').mkdir()
    (bundle / 'report/index.html').write_text('<a href="fine_grained.html">view</a>')
    (bundle / 'report/fine_grained.html').write_text('launch-a launch-b binary-a kernels.py')
    (root / 'receipt.json').write_text(json.dumps(receipt))
    (root / 'cohort.json').write_text(json.dumps(cohort))
    seal(bundle)
    return bundle


def seal(bundle):
    files = {str(p.relative_to(bundle)): dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
             for p in bundle.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    (bundle / 'manifest.json').write_text(json.dumps(dict(files=files)))


class C1ActorBinding(unittest.TestCase):
    def verify(self, bundle):
        return c.verify(bundle, bundle.parent/'receipt.json', bundle.parent/'cohort.json',
                        'ascend', 'runtime_recurrence', 0, 0)

    def test_end_to_end_exact_visits_null_control_both_aiv_slots_and_aic(self):
        for slot, kind in [(1, 'AIV'), (2, 'AIV'), (0, 'AIC')]:
            with self.subTest(slot=slot), tempfile.TemporaryDirectory() as tmp:
                result = self.verify(fixture(Path(tmp), slot, kind))
                self.assertEqual(result['status'], 'pass')
                self.assertTrue(result['runtime_loop']['same_binary'])

    def test_wrong_record_identity_semantic_slot_and_proof_rejected(self):
        changes = [lambda r: r['compiler_actor'].update(module_sha256='d'*64),
                   lambda r: r['compiler_actor'].update(compile_id='other'),
                   lambda r: r['compiler_actor'].update(function='other'),
                   lambda r: r.update(actor=0), lambda r: r.update(semantic='control_checkpoint'),
                   lambda r: r['compiler_actor']['binding_proof'].update(observed_actor_slot=1),
                   lambda r: r['compiler_actor']['binding_proof'].pop('runtime_slot_status'),
                   lambda r: r.update(site=800)]
        for n, change in enumerate(changes):
            with self.subTest(n=n), tempfile.TemporaryDirectory() as tmp:
                bundle = fixture(Path(tmp))
                doc = c.load(bundle/'ai/fine_grained.json')
                change(doc['records'][0])
                (bundle/'ai/fine_grained.json').write_text(json.dumps(doc))
                seal(bundle)
                with self.assertRaises(c.ContractError):
                    self.verify(bundle)

    def test_wrong_module_plan_cannot_borrow_actor_binary_semantic_or_selection(self):
        changes = [lambda e: e.update(module_sha256='d'*64), lambda e: e.update(compile_id='other'),
                   lambda e: e.update(binary_id='other'),
                   lambda e: e['compiler_actors'][0].update(function='other'),
                   lambda e: e['plan']['inventory'][0].update(public_semantic='issue'),
                   lambda e: e['plan']['inventory'][0].update(selected=False),
                   lambda e: e['plan'].update(max_sites=None),
                   lambda e: e['plan'].update(max_sites=0),
                   lambda e: e['plan'].update(candidate_count=0)]
        for n, change in enumerate(changes):
            with self.subTest(n=n), tempfile.TemporaryDirectory() as tmp:
                bundle = fixture(Path(tmp))
                doc = c.load(bundle/'ai/observation_plan.json')
                # A second unrelated entry offers the original numeric site;
                # union-by-binary or union-by-actor must not hide the corruption.
                unrelated = copy.deepcopy(doc['plans'][0])
                unrelated.update(binary_id='unrelated-binary')
                doc['plans'].append(unrelated)
                change(doc['plans'][0])
                (bundle/'ai/observation_plan.json').write_text(json.dumps(doc))
                seal(bundle)
                with self.assertRaises(c.ContractError):
                    self.verify(bundle)

    def test_control_null_policy_counts_reason_and_source_fail_closed(self):
        changes = [lambda e: e.update(plan_kind='operation'),
                   lambda e: e['plan'].update(policy='unknown'),
                   lambda e: e['plan'].update(candidate_count=0),
                   lambda e: e['plan'].update(record_capacity_per_actor=0),
                   lambda e: e['plan']['inventory'][0].update(source_file=''),
                   lambda e: e['plan']['inventory'][0].update(public_semantic='invented'),
                   lambda e: e['plan']['inventory'][0].update(selection_reason=''),
                   lambda e: e['plan']['inventory'].append(copy.deepcopy(e['plan']['inventory'][0]))]
        for n, change in enumerate(changes):
            with self.subTest(n=n), tempfile.TemporaryDirectory() as tmp:
                bundle = fixture(Path(tmp))
                doc = c.load(bundle/'ai/observation_plan.json')
                change(doc['plans'][1])
                (bundle/'ai/observation_plan.json').write_text(json.dumps(doc))
                seal(bundle)
                with self.assertRaises(c.ContractError):
                    self.verify(bundle)

    def test_raw_manifest_loss_clock_source_and_runtime_guards_remain(self):
        mutations = [('ai/binaries.json', lambda d: d[0]['compiler_metadata']['flagprism_ascend_handoff']['artifacts'][0].update(llir='tampered')),
                     ('ai/observations.json', lambda d: d['observations'][0]['original_record'].__setitem__(5, 1)),
                     ('ai/observations.json', lambda d: d['captures'][0].update(raw_sha256='0'*64)),
                     ('ai/observations.json', lambda d: d['captures'][0].update(counter_saturated=True)),
                     ('ai/fine_grained.json', lambda d: d['records'][0].update(duration_ns=10)),
                     ('ai/fine_grained.json', lambda d: d['records'][0].update(occurrence=99)),
                     ('ai/deadlines.json', lambda d: d['limits_seconds'].update(compile=121)),
                     ('ai/deadlines.json', lambda d: d.update(supervisor_worker_launches=2)),
                     ('ai/export_timing.json', lambda d: d.update(export_wall_s=61))]
        for n, (path, mutate) in enumerate(mutations):
            with self.subTest(n=n), tempfile.TemporaryDirectory() as tmp:
                bundle = fixture(Path(tmp))
                doc = c.load(bundle/path)
                mutate(doc)
                (bundle/path).write_text(json.dumps(doc))
                seal(bundle)
                with self.assertRaises(c.ContractError):
                    self.verify(bundle)
        with tempfile.TemporaryDirectory() as tmp:
            bundle = fixture(Path(tmp))
            (bundle/'ai/source.py').write_text('tampered')
            seal(bundle)
            with self.assertRaises(c.ContractError):
                self.verify(bundle)
        with tempfile.TemporaryDirectory() as tmp:
            bundle = fixture(Path(tmp))
            (bundle/'raw/compiler.ll').write_text('tampered')
            with self.assertRaises(c.ContractError):
                self.verify(bundle)

    def test_runner_authorization_is_closed_without_explicit_freeze(self):
        with self.assertRaises(c.ContractError):
            authorization.verify_authorization(Path(__file__).parent, {})

    def test_other_actor_same_binary_cannot_supply_missing_selected_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = fixture(Path(tmp))
            doc = c.load(bundle/'ai/observation_plan.json')
            borrowed = copy.deepcopy(doc['plans'][0])
            borrowed['compiler_actors'][0]['function'] = 'another_actor'
            borrowed['compiler_actors'][0]['identity'] = f"late_llvm:{borrowed['module_sha256']}:another_actor"
            borrowed['compiler_actors'][0]['runtime_actor_binding']['function'] = 'another_actor'
            doc['plans'][0]['plan']['inventory'][0]['site_id'] = 999
            doc['plans'].append(borrowed)
            (bundle/'ai/observation_plan.json').write_text(json.dumps(doc))
            seal(bundle)
            with self.assertRaisesRegex(c.ContractError, 'exact binary/module/compile/function/semantic'):
                self.verify(bundle)

    def test_coherent_raw_actor_word_cannot_move_to_another_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = fixture(Path(tmp))
            fine = c.load(bundle/'ai/fine_grained.json')
            original = c.load(bundle/'ai/observations.json')
            cid = fine['records'][0]['capture_id']
            # All normalized/original labels and proofs agree on slot1. Bytes
            # still live in slot2's segment; matching labels alone must fail.
            for row in fine['records']:
                if row['capture_id'] == cid:
                    row['actor'] = 1
                    row['compiler_actor']['binding_proof']['observed_actor_slot'] = 1
            for observation in original['observations']:
                if observation['capture_id'] == cid:
                    observation['actor_slot'] = 1
                    observation['compiler_site']['actor_slot'] = 1
                    observation['compiler_site']['compiler_actor']['binding_proof']['observed_actor_slot'] = 1
                    observation['original_record'][5] = 1
            capture = original['captures'][0]
            raw = bytearray(base64.b64decode(capture['raw_base64']))
            segment_words = fine['records'][0]['compiler_actor']['runtime_actor_binding']['segment_words']
            for n in range(capture['actors'][2]['committed']):
                struct.pack_into('<Q', raw, (2*segment_words + 4 + n*8 + 5)*8, 1)
            capture['raw_base64'] = base64.b64encode(raw).decode()
            capture['raw_sha256'] = sha(raw)
            capture['actors'][1]['binding_status'] = 'verified_by_committed_records'
            capture['actors'][1]['compiler_actors'] = capture['actors'][2]['compiler_actors']
            for path, doc in [('ai/observations.json', original), ('ai/fine_grained.json', fine)]:
                (bundle/path).write_text(json.dumps(doc))
            seal(bundle)
            with self.assertRaisesRegex(c.ContractError, 'raw actor word differs from actual segment|original observations differ from committed raw allocation'):
                self.verify(bundle)

    def test_new_q4_adapter_keeps_exact_visit_rule(self):
        def rows(a, b):
            return [dict(site=8, invocation_id=inv, program=0, actor=2, occurrence=n)
                    for inv, count in [('a', a), ('b', b)] for n in range(count)]
        self.assertEqual(dynamic.exact_runtime_sites(rows(2, 5)), [8])
        self.assertEqual(dynamic.exact_runtime_sites(rows(3, 6)), [8])
        with self.assertRaises(c.ContractError):
            dynamic.exact_runtime_sites(rows(1, 1))


if __name__ == '__main__':
    unittest.main()
