"""SDK schema/worker identity contracts; CPU tests run only in Docker."""
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest


def producer():
    path = Path(__file__).resolve(
    ).parents[1] / 'python/flagtree_profiler/cann_joint.py'
    spec = importlib.util.spec_from_file_location('cann_joint_producer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, *, sdk_thread=9, task_id=0):
    capture = tmp_path / 'PROF_fixture'
    (capture / 'host/sqlite').mkdir(parents=True)
    (capture / 'host/info.json').write_text('{"pid":7}')
    (capture / 'device_4').mkdir()
    (capture / 'device_4/info.json.4').write_text('{"DeviceInfo":[{"id":4}]}')
    connection = sqlite3.connect(capture / 'host/sqlite/runtime.db')
    connection.execute(
        'CREATE TABLE HostTask(device_id,stream_id,task_id,connection_id,thread_id)'
    )
    connection.execute('INSERT INTO HostTask VALUES (4,0,?,?,?)',
                       (task_id, 0, sdk_thread))
    connection.commit()
    connection.close()
    connection = sqlite3.connect(capture / 'msprof_fixture.db')
    connection.execute(
        'CREATE TABLE TASK(globalPid,deviceId,streamId,taskId,connectionId,globalTaskId,startNs,endNs)'
    )
    connection.execute('INSERT INTO TASK VALUES (7,4,0,?,0,0,100,120)',
                       (task_id, ))
    connection.commit()
    connection.close()
    receipt = {
        'token_id': 1,
        'scope_id': 0,
        'session_id': 0,
        'capture_epoch': 1,
        'status': 'collected',
        'publish_count': 1,
        'late_callback': False,
        'worker': {
            'abi_version': 1,
            'struct_size': 64,
            'process_id': 7,
            'thread_id': 9,
            'device_id': 4,
            'stream_id': 0,
            'task_id': task_id,
            'stream_handle': 0,
            'launch_status': 0,
            'device_query_status': 0,
            'stream_query_status': 0,
            'task_query_status': 0
        },
        'invocation_identity': {
            'invocation_id': 'launch-0',
            'binary_id': 'actual-compiler-hash',
            'scope_id': 0,
            'session_id': 0,
            'evidence': 'retained_per_launch_worker_receipt'
        },
    }
    receipt.update(collector_output_path=str(tmp_path),
                   sdk_capture_path=str(capture),
                   sdk_capture_binding_status='sealed_unique_sdk_capture',
                   sdk_capture_binding_evidence=json.dumps({
                       'kind':
                       'owned_native_sdk_directory_lifetime_v1',
                       'capture_epoch':
                       1,
                       'owned_output_root':
                       str(tmp_path),
                       'before_scan_complete':
                       True,
                       'after_scan_complete':
                       True,
                       'existing_at_sdk_start': [],
                       'observed_after_sdk_close': [str(capture)],
                       'new_capture_paths': [str(capture)],
                       'selected_device_id':
                       4,
                       'collector_process_id':
                       7,
                       'host_info_snapshot': {
                           'pid': 7
                       },
                       'device_info_snapshot': {
                           'DeviceInfo': [{
                               'id': 4
                           }]
                       }
                   }))
    return capture, receipt


def run(tmp_path, capture, receipts):
    file = tmp_path / 'capture.cann-launch-receipts.json'
    file.write_text(json.dumps({'schema_version': 1, 'receipts': receipts}))
    return producer().build_native_task_proofs(capture, file)


def test_worker_zero_ids_bind_exact_sdk_connection_and_keep_clock_unverified(
        tmp_path):
    capture, receipt = fixture(tmp_path)
    output = run(tmp_path, capture, [receipt])
    proof = output['task_identity_proofs'][0]
    assert proof['status'] == 'verified_task_identity'
    assert proof['native']['sdk_task']['connectionId'] == 0
    assert proof['native']['sdk_host_task']['thread_id'] == 9
    assert proof['clock_alignment'] == 'unverified'
    assert output['receipt_sha256'] and all(row['sha256']
                                            for row in output['raw_inputs'])


def test_wrong_worker_tid_does_not_use_scope_time_or_name(tmp_path):
    capture, receipt = fixture(tmp_path, sdk_thread=10)
    assert run(
        tmp_path, capture,
        [receipt])['task_identity_proofs'][0]['status'] == 'unassociated'


def test_missing_query_cannot_treat_default_zero_as_actual_task(tmp_path):
    capture, receipt = fixture(tmp_path)
    receipt['worker']['task_query_status'] = -1
    assert run(
        tmp_path, capture,
        [receipt])['task_identity_proofs'][0]['status'] == 'unassociated'


def test_two_source_invocations_cannot_share_one_sdk_task(tmp_path):
    capture, receipt = fixture(tmp_path)
    other = json.loads(json.dumps(receipt))
    other['token_id'] = 2
    other['scope_id'] = 1
    other['invocation_identity'].update(scope_id=1, invocation_id='launch-1')
    proofs = run(tmp_path, capture, [receipt, other])['task_identity_proofs']
    assert [proof['status'] for proof in proofs] == ['ambiguous', 'ambiguous']


def test_reused_task_id_across_sdk_captures_uses_exact_epoch_seal(tmp_path):
    import shutil
    capture, receipt = fixture(tmp_path)
    shutil.copytree(capture, tmp_path / 'PROF_other')
    proof = run(tmp_path, tmp_path, [receipt])['task_identity_proofs'][0]
    assert proof['status'] == 'verified_task_identity'
    assert proof['native']['capture_id'] == 'PROF_fixture'


def test_ambiguous_or_changed_sdk_epoch_metadata_is_not_a_certificate(
        tmp_path):
    capture, receipt = fixture(tmp_path)
    evidence = json.loads(receipt['sdk_capture_binding_evidence'])
    evidence['new_capture_paths'].append(str(tmp_path / 'PROF_other'))
    receipt['sdk_capture_binding_evidence'] = json.dumps(evidence)
    assert run(
        tmp_path, capture,
        [receipt])['task_identity_proofs'][0]['status'] == 'unassociated'
    evidence['new_capture_paths'] = [str(capture)]
    evidence['host_info_snapshot'] = {'pid': 8}
    receipt['sdk_capture_binding_evidence'] = json.dumps(evidence)
    assert run(
        tmp_path, capture,
        [receipt])['task_identity_proofs'][0]['status'] == 'unassociated'


@pytest.mark.parametrize('mutation', [
    'empty', 'wrong_path', 'old_folder', 'outside_root', 'epoch',
    'incomplete_scan'
])
def test_bad_epoch_seal_cannot_certify_matching_worker_ids(tmp_path, mutation):
    capture, receipt = fixture(tmp_path)
    evidence = json.loads(receipt['sdk_capture_binding_evidence'])
    if mutation == 'empty':
        receipt['sdk_capture_binding_status'] = 'unsealed'
        receipt['sdk_capture_binding_evidence'] = ''
    elif mutation == 'wrong_path':
        receipt['sdk_capture_path'] = str(tmp_path / 'PROF_wrong')
    elif mutation == 'old_folder':
        evidence['existing_at_sdk_start'] = [str(capture)]
    elif mutation == 'outside_root':
        receipt['collector_output_path'] = str(tmp_path / 'unrelated_owner')
        evidence['owned_output_root'] = receipt['collector_output_path']
    elif mutation == 'epoch':
        evidence['capture_epoch'] = 2
    else:
        evidence['before_scan_complete'] = False
    if mutation != 'empty':
        receipt['sdk_capture_binding_evidence'] = json.dumps(evidence)
    assert run(
        tmp_path, capture,
        [receipt])['task_identity_proofs'][0]['status'] == 'unassociated'


def test_duplicate_token_cannot_bind_two_native_tasks(tmp_path):
    capture, receipt = fixture(tmp_path)
    other = json.loads(json.dumps(receipt))
    other['worker']['task_id'] = 1
    other['scope_id'] = 1
    other['invocation_identity'].update(scope_id=1, invocation_id='launch-1')
    connection = sqlite3.connect(capture / 'host/sqlite/runtime.db')
    connection.execute('INSERT INTO HostTask VALUES (4,0,1,1,9)')
    connection.commit()
    connection.close()
    connection = sqlite3.connect(capture / 'msprof_fixture.db')
    connection.execute('INSERT INTO TASK VALUES (7,4,0,1,1,1,140,160)')
    connection.commit()
    connection.close()
    assert [
        proof['status'] for proof in run(tmp_path, capture, [receipt, other])
        ['task_identity_proofs']
    ] == ['ambiguous', 'ambiguous']


def contextual_fixture(tmp_path,
                       *,
                       compute_ids=(0, ),
                       context_ids=(0, 4294967295)):
    capture, receipt = fixture(tmp_path)
    connection = sqlite3.connect(capture / 'host/sqlite/runtime.db')
    connection.execute('ALTER TABLE HostTask ADD COLUMN context_ids')
    connection.execute('ALTER TABLE HostTask ADD COLUMN model_id')
    connection.execute('ALTER TABLE HostTask ADD COLUMN batch_id')
    connection.execute('DELETE FROM HostTask')
    for context in context_ids:
        connection.execute(
            'INSERT INTO HostTask VALUES (4,0,0,0,9,?,4294967295,0)',
            (str(context), ))
    connection.commit()
    connection.close()
    connection = sqlite3.connect(capture / 'msprof_fixture.db')
    connection.execute('ALTER TABLE TASK ADD COLUMN contextId')
    connection.execute('ALTER TABLE TASK ADD COLUMN modelId')
    connection.execute('DELETE FROM TASK')
    for index, context in enumerate(context_ids):
        connection.execute(
            'INSERT INTO TASK VALUES (7,4,0,0,0,?,100,120,?,4294967295)',
            (index, context))
    connection.execute(
        'CREATE TABLE COMPUTE_TASK_INFO(globalTaskId,blockNum,mixBlockNum)')
    for index in compute_ids:
        connection.execute('INSERT INTO COMPUTE_TASK_INFO VALUES (?,64,128)',
                           (index, ))
    connection.commit()
    connection.close()
    return capture, receipt


def test_mix_context_membership_and_compute_fk_select_zero_keep_all_views(
        tmp_path):
    capture, receipt = contextual_fixture(tmp_path)
    output = run(tmp_path, capture, [receipt])
    proof = output['task_identity_proofs'][0]
    assert proof['status'] == 'verified_task_identity'
    assert proof['native']['sdk_task']['globalTaskId'] == 0
    evidence = proof['dispatch_context_evidence']
    assert evidence['compute_member_count'] == 1
    assert evidence['selected_compute_global_task_id'] == 0
    assert len(evidence['all_context_views']) == 2
    assert 'context_id' not in evidence['dispatch_key']
    assert output['raw_compute_task_inventory'] == [{
        'capture_id': '.',
        'sdk_compute_task_info': {
            'globalTaskId': 0,
            'blockNum': 64,
            'mixBlockNum': 128
        }
    }]
    assert output['compute_task_info_captures'] == ['.']


def test_uintmax_context_can_be_real_compute_and_singleton_has_evidence(
        tmp_path):
    capture, receipt = contextual_fixture(tmp_path, context_ids=(4294967295, ))
    proof = run(tmp_path, capture, [receipt])['task_identity_proofs'][0]
    assert proof['status'] == 'verified_task_identity'
    assert proof['native']['sdk_task']['contextId'] == 4294967295
    assert len(proof['dispatch_context_evidence']['all_context_views']) == 1


def test_multi_compute_dispatch_is_explicitly_unsupported(tmp_path):
    capture, receipt = contextual_fixture(tmp_path, compute_ids=(0, 1))
    proof = run(tmp_path, capture, [receipt])['task_identity_proofs'][0]
    assert proof['status'] == 'compound_dispatch_unsupported'
    assert 'native' not in proof
    assert proof['dispatch_context_evidence']['compute_member_count'] == 2
    assert proof['dispatch_context_evidence'][
        'selected_compute_global_task_id'] is None


def test_empty_compute_table_does_not_promote_container_to_compute(tmp_path):
    capture, receipt = contextual_fixture(tmp_path, compute_ids=())
    output = run(tmp_path, capture, [receipt])
    assert output['compute_task_info_captures'] == ['.']
    assert output['task_identity_proofs'][0]['status'] == 'unassociated'


@pytest.mark.parametrize('mutation', [
    'model', 'wrong_context', 'nondecimal', 'duplicate', 'out_of_range',
    'negative'
])
def test_context_membership_rejects_invalid_sdk_join(tmp_path, mutation):
    capture, receipt = contextual_fixture(tmp_path, context_ids=(0, ))
    connection = sqlite3.connect(capture / 'host/sqlite/runtime.db')
    if mutation == 'model':
        connection.execute('UPDATE HostTask SET model_id=3')
    else:
        value = {
            'wrong_context': '1',
            'nondecimal': '0x0',
            'duplicate': '0,0',
            'out_of_range': '4294967296',
            'negative': '-1'
        }[mutation]
        connection.execute('UPDATE HostTask SET context_ids=?', (value, ))
    connection.commit()
    connection.close()
    assert run(
        tmp_path, capture,
        [receipt])['task_identity_proofs'][0]['status'] == 'unassociated'


def test_compute_fk_ambiguity_does_not_select_by_first_row(tmp_path):
    capture, receipt = contextual_fixture(tmp_path, context_ids=(0, ))
    connection = sqlite3.connect(capture / 'msprof_fixture.db')
    connection.execute('INSERT INTO COMPUTE_TASK_INFO VALUES (0,32,64)')
    connection.commit()
    connection.close()
    output = run(tmp_path, capture, [receipt])
    assert len(output['raw_compute_task_inventory']) == 2
    assert output['task_identity_proofs'][0]['status'] == 'unassociated'
