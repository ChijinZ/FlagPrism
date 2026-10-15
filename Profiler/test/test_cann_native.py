"""Exact SDK TASK/worker/source proofs and conservative export-view deduplication."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3

import pytest

from flagtree.profiler.cann_joint import build_native_task_proofs
from flagtree.profiler.cann_native import augment_native_tasks, normalize_legacy_activity_kinds
from flagtree.profiler._report import analyze, render, write_bundle


def fixture(tmp_path):
    spec = importlib.util.spec_from_file_location(
        'cann_joint_test_fixture',
        Path(__file__).with_name('test_cann_joint.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    capture, receipt = module.fixture(tmp_path)
    with sqlite3.connect(capture / 'host/sqlite/runtime.db') as db:
        db.execute('ALTER TABLE HostTask ADD COLUMN task_type')
        db.execute("UPDATE HostTask SET task_type='KERNEL_AIVEC'")
    with sqlite3.connect(capture / 'msprof_fixture.db') as db:
        db.execute('ALTER TABLE TASK ADD COLUMN taskType')
        db.execute('UPDATE TASK SET taskType=16')
    receipt_file = tmp_path / 'capture.cann-launch-receipts.json'
    receipt_file.write_text(
        json.dumps({
            'schema_version': 1,
            'receipts': [receipt]
        }))
    proof = build_native_task_proofs(capture, receipt_file)
    document = {
        'backend':
        'cann',
        'associations': [],
        'launches': [{
            'id': 'launch-0',
            'scope_id': 0,
            'session_id': 0,
            'binary_id': 'actual-compiler-hash',
            'arguments': {}
        }],
        'binaries': [{
            'id': 'actual-compiler-hash'
        }]
    }
    return capture, receipt, receipt_file, proof, document


def legacy(capture, **updates):
    path = capture / 'op_summary_fixture.csv'
    path.write_text('retained SDK export fixture\n')
    row = {
        'source': 'aclprof_op_summary',
        'state': 'collected',
        'metrics': {
            'activity.kind': 'kernel',
            'input_file': str(path),
            'device_id': 4,
            'stream_id': 0,
            'task_id': 0
        },
        'runtime_event': {
            'op_name': 'same_name',
            'device_id': 4,
            'stream_id': 0,
            'task_id': 0,
            'scope_id': 0,
            'correlation_id': 0,
            'start_time_ns': 100,
            'end_time_ns': 120
        }
    }
    row['metrics'].update(updates)
    return row


def canonical(output):
    return [
        r for r in output['associations'] if r['source'] == 'cann_sdk_task'
    ]


def test_zero_task_stream_scope_connection_exact_direct_invocation(tmp_path):
    _, _, _, proof, document = fixture(tmp_path)
    before = deepcopy(document)
    output = augment_native_tasks(document, proof)
    assert document == before
    event = analyze(output)['events'][0]
    assert all(event[k] == 0
               for k in ('task_id', 'scope_id', 'correlation_id', 'stream_id'))
    assert event['launch_id'] == 'launch-0'
    assert event['binary_id'] == 'actual-compiler-hash'
    assert event['metrics']['activity.clock_alignment'] == 'unverified'
    assert event['metrics'][
        'activity.duration_scope'] == 'whole_task_lifecycle_not_actor_occupancy'


def test_legacy_zero_remains_unknown_without_matching_typed_declaration(
        tmp_path):
    capture, _, _, _, document = fixture(tmp_path)
    document['associations'] = [legacy(capture)]
    event = analyze(document)['events'][0]
    assert all(event[k] is None
               for k in ('task_id', 'scope_id', 'correlation_id'))
    for row in document['associations']:
        row['metrics'].update({
            'activity.task_id': 1,
            'activity.scope_id': False
        })
    assert analyze(document)['events'][0]['task_id'] is None
    assert analyze(document)['events'][0]['scope_id'] is None


@pytest.mark.parametrize('field,value',
                         [('session_id', 1), ('capture_epoch', 2),
                          ('token_id', 2), ('scope_id', 1),
                          ('binary_id', 'other'), ('invocation_id', 'other')])
def test_wrong_retained_source_proof_never_binds(tmp_path, field, value):
    _, _, _, proof, document = fixture(tmp_path)
    proof['task_identity_proofs'][0][field] = value
    row = canonical(augment_native_tasks(document, proof))[0]
    assert row['invocation_identity'] is None
    assert row['metrics']['activity.association'] == 'unassociated'
    assert row['metrics']['activity.association_reason']


@pytest.mark.parametrize(
    'field', ['process_id', 'thread_id', 'device_id', 'stream_id', 'task_id'])
def test_wrong_worker_tuple_is_not_a_name_or_time_join(tmp_path, field):
    _, _, _, proof, document = fixture(tmp_path)
    proof['task_identity_proofs'][0]['worker'][field] += 1
    assert canonical(augment_native_tasks(
        document, proof))[0]['invocation_identity'] is None


def test_native_proof_must_equal_complete_candidate_and_duplicate_proofs_reject(
        tmp_path):
    _, _, _, proof, document = fixture(tmp_path)
    # The public producer is persisted as JSON. Break the in-memory builder's
    # shared row references exactly as that actual artifact boundary does.
    changed = json.loads(json.dumps(proof))
    changed['task_identity_proofs'][0]['native']['sdk_task']['startNs'] += 1
    assert canonical(augment_native_tasks(
        document, changed))[0]['invocation_identity'] is None
    proof['task_identity_proofs'].append(
        deepcopy(proof['task_identity_proofs'][0]))
    assert canonical(augment_native_tasks(
        document, proof))[0]['invocation_identity'] is None


def test_receipt_hash_or_missing_file_disables_source_but_retains_native(
        tmp_path):
    _, _, path, proof, document = fixture(tmp_path)
    path.write_text(path.read_text() + ' ')
    output = augment_native_tasks(document, proof)
    assert len(canonical(output)) == 1
    assert 'SHA256' in canonical(
        output)[0]['metrics']['activity.association_reason']
    path.unlink()
    assert canonical(augment_native_tasks(
        document, proof))[0]['invocation_identity'] is None


def test_same_name_same_scope_different_binary_uses_exact_direct_ids(tmp_path):
    capture, receipt, path, _, document = fixture(tmp_path)
    with sqlite3.connect(capture / 'host/sqlite/runtime.db') as db:
        db.execute("INSERT INTO HostTask VALUES (4,0,1,1,9,'KERNEL_AIVEC')")
    with sqlite3.connect(capture / 'msprof_fixture.db') as db:
        db.execute('INSERT INTO TASK VALUES (7,4,0,1,1,1,200,220,16)')
    second = deepcopy(receipt)
    second.update(token_id=2)
    second['worker']['task_id'] = 1
    second['invocation_identity'].update(invocation_id='launch-1',
                                         binary_id='binary-two')
    path.write_text(
        json.dumps({
            'schema_version': 1,
            'receipts': [receipt, second]
        }))
    document['launches'].append({
        'id': 'launch-1',
        'scope_id': 0,
        'session_id': 0,
        'binary_id': 'binary-two',
        'arguments': {}
    })
    document['binaries'].append({'id': 'binary-two'})
    proof = build_native_task_proofs(capture, path)
    events = analyze(augment_native_tasks(document, proof))['events']
    assert {(e['launch_id'], e['binary_id'])
            for e in events} == {('launch-0', 'actual-compiler-hash'),
                                 ('launch-1', 'binary-two')}


def test_exact_inventory_unique_no_pid_view_supersedes_with_audit(tmp_path):
    capture, _, _, proof, document = fixture(tmp_path)
    old = legacy(capture)
    document['associations'] = [old]
    output = augment_native_tasks(document, proof)
    assert len(output['associations']) == 1
    assert output['cann_native_superseded_views'][0]['row'] == old


def test_no_pid_ambiguous_inventory_is_retained_and_known_pid_can_disambiguate(
        tmp_path):
    capture, receipt, path, _, document = fixture(tmp_path)
    with sqlite3.connect(capture / 'msprof_fixture.db') as db:
        db.execute('INSERT INTO TASK VALUES (8,4,0,0,2,2,300,320,16)')
    proof = build_native_task_proofs(capture, path)
    assert len(proof['raw_native_task_inventory']) == 2
    document['associations'] = [legacy(capture)]
    assert len(augment_native_tasks(document, proof)['associations']) == 2
    document['associations'][0]['metrics']['activity.process_id'] = 7
    assert len(augment_native_tasks(document, proof)['associations']) == 1


def test_foreign_capture_or_missing_declared_tuple_cannot_be_deduplicated(
        tmp_path):
    capture, _, _, proof, document = fixture(tmp_path)
    row = legacy(capture)
    row['metrics']['input_file'] = str(tmp_path / 'foreign' / 'op_summary.csv')
    other = legacy(capture)
    del other['metrics']['task_id']
    document['associations'] = [row, other]
    assert len(augment_native_tasks(document, proof)['associations']) == 3


def test_ambiguous_host_task_stays_in_raw_inventory_but_not_canonical(
        tmp_path):
    capture, _, path, _, document = fixture(tmp_path)
    with sqlite3.connect(capture / 'host/sqlite/runtime.db') as db:
        db.execute("INSERT INTO HostTask VALUES (4,0,0,0,10,'KERNEL_AIVEC')")
    proof = build_native_task_proofs(capture, path)
    assert len(proof['raw_native_task_inventory']) == 1
    assert proof['native_task_candidates'] == []
    document['associations'] = [legacy(capture)]
    assert augment_native_tasks(
        document, proof)['associations'] == document['associations']


def test_invalid_direct_proof_does_not_fall_back_to_positive_scope(tmp_path):
    _, _, _, proof, document = fixture(tmp_path)
    output = augment_native_tasks(document, proof)
    row = canonical(output)[0]
    document['launches'][0]['scope_id'] = 1
    output['launches'][0]['scope_id'] = 1
    row['runtime_event']['scope_id'] = 1
    row['metrics']['activity.scope_id'] = 1
    row['invocation_identity']['scope_id'] = 1
    row['invocation_identity']['binary_id'] = 'wrong'
    assert 'launch_id' not in analyze(output)['events'][0]


def test_actual_retained_r3_archive_offline_builder_and_report(tmp_path):
    value = os.environ.get('FLAGPRISM_CANN_NATIVE_FIXTURE')
    if not value:
        pytest.skip(
            'Set FLAGPRISM_CANN_NATIVE_FIXTURE to the retained actual r3 archive'
        )
    base = Path(value)
    raw = base / 'capture/raw/native'
    assert (raw / 'capture.cann-launch-receipts.json').is_file()
    document = json.loads((raw / 'capture.vendor.json').read_text())
    snapshot = json.loads((raw / 'capture.launches.json').read_text())
    document.update({
        key: snapshot[key]
        for key in ('launches', 'binaries', 'software', 'metadata_rejections')
    })
    proof = build_native_task_proofs(
        base / 'aclprof/flagtree_profiler_session_0',
        raw / 'capture.cann-launch-receipts.json')
    assert len(proof['sealed_capture_ids']) == 1
    assert len(proof['native_task_candidates']) == 4
    output = augment_native_tasks(document, proof)
    report = analyze(output)
    events = [e for e in report['events'] if e['kind'] == 'kernel']
    assert len(events) == 4
    assert {e['launch_id']
            for e in events
            } == {'launch-1', 'launch-2', 'launch-3', 'launch-4'}
    assert len({e['binary_id'] for e in events}) == 2
    assert sum(e['task_id'] == 0 for e in events) == 2
    assert len(output['cann_native_superseded_views']) == 6
    (tmp_path / 'native-task-report.html').write_text(render(report))
    write_bundle(report, output, tmp_path / 'offline-bundle')
    retained = [
        json.loads(line) for line in (
            tmp_path /
            'offline-bundle/ai/events.jsonl').read_text().splitlines()
    ]
    retained = [row for row in retained if row['kind'] == 'kernel']
    audit = json.loads(
        (tmp_path / 'offline-bundle/ai/cann_native_tasks.json').read_text())
    assert len(audit['superseded_views']) == 6
    assert {row['launch_id']
            for row in retained
            } == {'launch-1', 'launch-2', 'launch-3', 'launch-4'}
    assert all(e['metrics']['activity.clock_alignment'] == 'unverified'
               for e in events)


def test_nested_sdk_manifest_is_in_global_sha_inventory(tmp_path):
    import hashlib
    from flagtree.profiler._report import write_manifest
    (tmp_path / 'ai').mkdir()
    (tmp_path / 'ai/summary.json').write_text('{"availability":{}}')
    nested = tmp_path / 'raw/sdk/manifest.json'
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b'{"actual_sdk_manifest":true}')
    write_manifest(tmp_path, {})
    result = json.loads((tmp_path / 'manifest.json').read_text())
    assert result['files']['raw/sdk/manifest.json'][
        'sha256'] == hashlib.sha256(nested.read_bytes()).hexdigest()
    assert 'manifest.json' not in result['files']


@pytest.mark.parametrize('task_type,host_type', [(1, 'MEMCPY'), (16, 'MEMCPY'),
                                                 (None, None),
                                                 (77, 'UNKNOWN')])
def test_non_kernel_or_unknown_task_type_stays_raw_and_does_not_supersede(
        tmp_path, task_type, host_type):
    capture, _, path, _, document = fixture(tmp_path)
    with sqlite3.connect(capture / 'msprof_fixture.db') as db:
        db.execute('UPDATE TASK SET taskType=?', (task_type, ))
    with sqlite3.connect(capture / 'host/sqlite/runtime.db') as db:
        db.execute('UPDATE HostTask SET task_type=?', (host_type, ))
    proof = build_native_task_proofs(capture, path)
    document['associations'] = [legacy(capture)]
    output = augment_native_tasks(document, proof)
    assert canonical(output) == []
    assert output['associations'] == document['associations']
    assert output['cann_native_unclassified_tasks'][0]['reason']


@pytest.mark.parametrize(
    'field', ['device_id', 'stream_id', 'task_id', 'activity.task_id'])
def test_explicit_unknown_mask_blocks_dedup_even_with_typed_zero(
        tmp_path, field):
    capture, _, _, proof, document = fixture(tmp_path)
    row = legacy(capture)
    row['metrics'].update({
        'activity.unknown_fields': field,
        'activity.task_id': 0
    })
    document['associations'] = [row]
    assert len(augment_native_tasks(document, proof)['associations']) == 2


def test_repeated_augmentation_keeps_one_exact_native_inventory(tmp_path):
    _, _, _, proof, document = fixture(tmp_path)
    first = augment_native_tasks(document, proof)
    second = augment_native_tasks(first, proof)
    assert len(second['associations']) == 1
    assert second['associations'] == first['associations']


@pytest.mark.parametrize('opaque_type', [16, 77, None])
def test_task_numeric_enum_is_opaque_and_host_kernel_enum_is_authoritative(
        tmp_path, opaque_type):
    capture, _, path, _, document = fixture(tmp_path)
    with sqlite3.connect(capture / 'msprof_fixture.db') as db:
        db.execute('UPDATE TASK SET taskType=?', (opaque_type, ))
    output = augment_native_tasks(document,
                                  build_native_task_proofs(capture, path))
    assert len(canonical(output)) == 1
    assert canonical(
        output)[0]['metrics']['sdk_task']['taskType'] == opaque_type


@pytest.mark.parametrize('host_type,task_class',
                         [('KERNEL_AICORE', 'AI_CORE'),
                          ('KERNEL_AIVEC', 'AI_VECTOR_CORE'),
                          ('KERNEL_MIX_AIC', 'MIX_AIC'),
                          ('KERNEL_MIX_AIV', 'MIX_AIV'),
                          ('KERNEL_AICPU', 'AI_CPU')])
def test_installed_sdk_exact_kernel_enum_map(tmp_path, host_type, task_class):
    capture, _, path, _, document = fixture(tmp_path)
    with sqlite3.connect(capture / 'host/sqlite/runtime.db') as db:
        db.execute('UPDATE HostTask SET task_type=?', (host_type, ))
    output = augment_native_tasks(document,
                                  build_native_task_proofs(capture, path))
    assert canonical(output)[0]['metrics']['activity.task_class'] == task_class
    assert output['capture']['cann_native_tasks'][
        'kernel_classification_source']['table'] == 'RTS_TASK_TYPE_MAP'


@pytest.mark.parametrize('declared', [{
    'activity.device_id': 5
}, {
    'activity.stream_id': 1
}, {
    'activity.task_id': 1
}, {
    'process_id': 8
}, {
    'connection_id': 2
}, {
    'activity.process_id': 7,
    'process_id': 8
}])
def test_conflicting_declared_identity_is_not_hidden_by_other_fields(
        tmp_path, declared):
    capture, _, _, proof, document = fixture(tmp_path)
    document['associations'] = [legacy(capture, **declared)]
    assert len(augment_native_tasks(document, proof)['associations']) == 2


@pytest.mark.parametrize('task_type,kind',
                         [('AI_VECTOR_CORE', 'kernel'),
                          ('KERNEL_AICORE', 'kernel'),
                          ('PROFILER_TRACE_EX', 'profiler_marker'),
                          ('EVENT_RECORD', 'device_event_record'),
                          ('PCIE_DMA_SQE', 'memcpy'),
                          ('kernel_looking_name', 'unclassified_device_task'),
                          (16, 'unclassified_device_task'),
                          (None, 'unclassified_device_task')])
def test_legacy_exact_sdk_task_type_without_source_proof(
        tmp_path, task_type, kind):
    capture, _, _, _, document = fixture(tmp_path)
    row = legacy(capture)
    row['runtime_event']['op_name'] = 'misleading_kernel_name'
    row['metrics']['raw_event_json'] = json.dumps({
        'args': {
            'Task Type': task_type,
            'size(B)': 49248,
            'operation': 'device to host'
        }
    })
    document['associations'] = [row]
    original = deepcopy(document)
    output = normalize_legacy_activity_kinds(document)
    assert document == original
    assert output['associations'][0]['metrics']['activity.kind'] == kind
    report = analyze(output)
    assert sum(e['kind'] == 'kernel'
               for e in report['events']) == (kind == 'kernel')
    if kind == 'memcpy':
        event = report['events'][0]
        assert event['metrics']['activity.bytes'] == 49248
        assert event['metrics']['activity.copy_direction'] == 'device_to_host'
        assert 'launch_id' not in event
    if kind in ('profiler_marker', 'device_event_record',
                'unclassified_device_task'):
        assert output['cann_native_activity_extensions'][0][
            'original_row'] == row
        assert report['events'] == []
        write_bundle(report, output, tmp_path / 'classified')
        retained = json.loads(
            (tmp_path / 'classified/ai/cann_native_tasks.json').read_text())
        assert retained['activity_extensions'][0]['kind'] == kind


def test_host_runtime_without_device_task_type_is_unchanged(tmp_path):
    capture, _, _, _, document = fixture(tmp_path)
    row = legacy(capture)
    row['metrics']['activity.kind'] = 'runtime'
    row['metrics']['raw_event_json'] = '{"args":{"Mode":"ACL_RTS"}}'
    document['associations'] = [row]
    assert normalize_legacy_activity_kinds(document)['associations'] == [row]


def test_actual_hidden_r4_taxonomy_without_task_or_source_proof(tmp_path):
    value = os.environ.get('FLAGPRISM_CANN_NATIVE_HIDDEN_VENDOR')
    if not value:
        pytest.skip(
            'Set FLAGPRISM_CANN_NATIVE_HIDDEN_VENDOR to the actual retained hidden-r4 vendor file'
        )
    raw = Path(value).read_bytes()
    document = json.loads(raw)
    output = normalize_legacy_activity_kinds(document)
    report = analyze(output)
    kernels = [e for e in report['events'] if e['kind'] == 'kernel']
    copies = [e for e in report['events'] if e['kind'] == 'memcpy']
    assert len(kernels) == 4 and len(copies) == 4
    assert all(e['metrics']['activity.bytes'] == 49248 for e in copies)
    assert all(e['metrics']['activity.copy_direction'] == 'device_to_host'
               for e in copies)
    assert all('launch_id' not in e for e in kernels + copies)
    counts = output['capture']['cann_native_activity_kinds']['counts']
    assert counts == {
        'kernel': 4,
        'memcpy': 4,
        'profiler_marker': 8,
        'device_event_record': 2
    }
    assert len(output['cann_native_activity_extensions']) == 10
    assert normalize_legacy_activity_kinds(output) == output
    write_bundle(report, output, tmp_path / 'hidden-r4-offline')
    saved = json.loads(
        (tmp_path / 'hidden-r4-offline/ai/cann_native_tasks.json').read_text())
    assert len(saved['activity_extensions']) == 10
