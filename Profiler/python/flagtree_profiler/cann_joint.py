"""Produce exact native SDK task identity from retained launch-worker receipts.

SDK identity is joined by actual IDs/connection tables, never by a name, order
or source tick containment. This producer does not certify SYS clock alignment;
SDK-converted task times alone do not establish the original counter domain.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3


def _database_rows(path, table, inputs, root):
    if not path.is_file():
        return []
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro',
                                 uri=True)
    try:
        connection.row_factory = sqlite3.Row
        present = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table, )).fetchone()
        if not present:
            return []
        inputs.append({
            'path': str(path.relative_to(root)),
            'sha256': digest,
            'table': table
        })
        return [
            dict(row)
            for row in connection.execute('SELECT * FROM "' + table + '"')
        ]
    finally:
        connection.close()


def _worker_is_valid(receipt):
    worker = receipt.get('worker') or {}
    return (
        isinstance(worker, dict) and receipt.get('status') == 'collected'
        and all(
            type(receipt.get(key)) is int and 0 <= receipt[key] < 2**64
            for key in ('token_id', 'scope_id', 'session_id', 'capture_epoch'))
        and receipt.get('publish_count') == 1
        and receipt.get('late_callback') is False
        and type(worker.get('abi_version')) is int
        and worker['abi_version'] == 1
        and type(worker.get('struct_size')) is int
        and worker['struct_size'] == 64 and all(
            type(worker.get(key)) is int and worker[key] == 0
            for key in ('launch_status', 'device_query_status',
                        'stream_query_status', 'task_query_status')) and all(
                            type(worker.get(key)) is int and worker[key] > 0
                            for key in ('process_id', 'thread_id'))
        and all(
            type(worker.get(key)) is int and worker[key] >= 0
            for key in ('device_id', 'stream_id', 'task_id', 'stream_handle')))


def _sealed_capture(receipt, inputs, root):
    """Validate collector-produced SDK lifetime metadata, not a caller label."""
    if receipt.get(
            'sdk_capture_binding_status') != 'sealed_unique_sdk_capture':
        return None
    evidence = json.loads(
        receipt.get('sdk_capture_binding_evidence') or 'null')
    if not isinstance(evidence, dict):
        return None
    if (evidence.get('kind') != 'owned_native_sdk_directory_lifetime_v1'
            or type(receipt.get('capture_epoch')) is not int
            or receipt['capture_epoch'] <= 0
            or evidence.get('capture_epoch') != receipt['capture_epoch']
            or evidence.get('before_scan_complete') is not True
            or evidence.get('after_scan_complete') is not True):
        return None
    path_value = receipt.get('sdk_capture_path')
    output_value = receipt.get('collector_output_path')
    if not isinstance(path_value, str) or not path_value or not output_value:
        return None
    capture = Path(path_value).resolve()
    output = Path(output_value).resolve()
    created = evidence.get('new_capture_paths')
    before = evidence.get('existing_at_sdk_start')
    after = evidence.get('observed_after_sdk_close')
    if not all(isinstance(value, list) for value in (created, before, after)):
        return None
    if (len(created) != 1 or Path(created[0]).resolve() != capture
            or capture not in [Path(value).resolve() for value in after]
            or capture in [Path(value).resolve() for value in before]
            or Path(evidence.get('owned_output_root', '')).resolve() != output
            or output not in capture.parents
            or not (capture == root or root in capture.parents)):
        return None
    worker = receipt['worker']
    if (evidence.get('collector_process_id') != worker['process_id']
            or evidence.get('selected_device_id') != worker['device_id']):
        return None
    host_path = capture / 'host/info.json'
    device_path = capture / f'device_{worker["device_id"]}/info.json.{worker["device_id"]}'
    snapshots = []
    for path, field in ((host_path, 'host_info_snapshot'),
                        (device_path, 'device_info_snapshot')):
        if not path.is_file():
            return None
        raw = path.read_bytes()
        value = json.loads(raw)
        if value != evidence.get(field):
            return None
        inputs.append({
            'path': str(path.relative_to(root)),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'kind': 'sealed_sdk_metadata'
        })
        snapshots.append(value)
    try:
        pid = int(snapshots[0].get('pid'))
    except (TypeError, ValueError):
        return None
    devices = [
        row for row in snapshots[1].get('DeviceInfo', [])
        if row.get('id') == worker['device_id']
    ]
    if pid != worker['process_id'] or len(devices) != 1:
        return None
    return str(capture.relative_to(root))


def build_native_task_proofs(capture_root, receipt_file):
    """Read actual SDK export plus the native finalizer's receipt artifact.

    The file must be the producer's per-session `.cann-launch-receipts.json`.
    Its root finalizer binds the retained scope token to one source invocation.
    Every SDK candidate remains qualified by its enclosing PROF capture. Raw
    file hashes and complete selected rows are kept as reviewable provenance.
    """
    root = Path(capture_root).resolve()
    receipt_path = Path(receipt_file).resolve()
    payload = receipt_path.read_bytes()
    document = json.loads(payload)
    if document.get('schema_version') != 1:
        raise ValueError('unsupported CANN launch receipt artifact schema')
    receipt_digest = hashlib.sha256(payload).hexdigest()
    capture_paths = sorted(
        {path.parent.parent
         for path in root.rglob('host/info.json')})
    if root.joinpath('host').is_dir():
        capture_paths = sorted(set(capture_paths) | {root})
    inputs = []
    native = []
    inventory = []
    for capture in capture_paths:
        host_info = capture / 'host/info.json'
        if not host_info.is_file():
            continue
        json.loads(host_info.read_text())
        inputs.append({
            'path':
            str(host_info.relative_to(root)),
            'sha256':
            hashlib.sha256(host_info.read_bytes()).hexdigest()
        })
        # SDK's consolidated TASK keeps the real process ID. HostTask keeps the
        # actual launch-worker TID and connection tuple in the same capture.
        host_tasks = _database_rows(capture / 'host/sqlite/runtime.db',
                                    'HostTask', inputs, root)
        consolidated = []
        for database in sorted(capture.glob('msprof_*.db')):
            consolidated.extend(_database_rows(database, 'TASK', inputs, root))
        for task in consolidated:
            inventory_entry = {
                'capture_id': str(capture.relative_to(root)),
                'sdk_task': task
            }
            if inventory_entry not in inventory:
                inventory.append(inventory_entry)
            peers = [
                row for row in host_tasks if all(
                    row.get(left) == task.get(right)
                    for left, right in (('connection_id', 'connectionId'),
                                        ('device_id', 'deviceId'),
                                        ('stream_id', 'streamId'), ('task_id',
                                                                    'taskId')))
            ]
            if len(peers) != 1:
                continue
            # Deduplicate identical SDK export views, retaining their file
            # evidence. Different context/global-task/time rows remain distinct.
            entry = {
                'capture_id': str(capture.relative_to(root)),
                'sdk_task': task,
                'sdk_host_task': peers[0]
            }
            if entry not in native:
                native.append(entry)
    proofs = []
    sealed_capture_ids = set()
    for receipt in document.get('receipts', []):
        identity = receipt.get('invocation_identity')
        result = {
            'token_id':
            receipt.get('token_id'),
            'scope_id':
            receipt.get('scope_id'),
            'session_id':
            receipt.get('session_id'),
            'capture_epoch':
            receipt.get('capture_epoch'),
            'invocation_id':
            identity.get('invocation_id')
            if isinstance(identity, dict) else None,
            'status':
            'unassociated',
            'clock_alignment':
            'unverified',
            'reason':
            'missing successful retained worker/source identity'
        }
        if (_worker_is_valid(receipt) and isinstance(identity, dict)
                and identity.get('evidence')
                == 'retained_per_launch_worker_receipt'
                and identity.get('binary_id') and identity.get('invocation_id')
                and identity.get('scope_id') == receipt.get('scope_id')
                and identity.get('session_id') == receipt.get('session_id')):
            worker = receipt['worker']
            sdk_capture = _sealed_capture(receipt, inputs, root)
            if sdk_capture is not None:
                sealed_capture_ids.add(sdk_capture)
            matches = [
                entry for entry in native
                if entry['capture_id'] == sdk_capture and all(
                    entry['sdk_task'].get(key) == worker[field]
                    for key, field in (('globalPid', 'process_id'),
                                       ('deviceId', 'device_id'),
                                       ('streamId', 'stream_id'),
                                       ('taskId', 'task_id'))) and
                entry['sdk_host_task'].get('thread_id') == worker['thread_id']
            ]
            if len(matches) == 1:
                selected = matches[0]
                result.update(
                    status='verified_task_identity',
                    reason=None,
                    binary_id=identity['binary_id'],
                    native=selected,
                    worker=dict(worker),
                    sdk_capture_binding_evidence=json.loads(
                        receipt['sdk_capture_binding_evidence']),
                    evidence_kind=
                    'retained_worker_token_and_sdk_connection_tables')
            else:
                result['reason'] = 'SDK task identity is missing or ambiguous'
                result['candidate_count'] = len(matches)
        proofs.append(result)
    # A stale last-task query or reused token cannot bind one SDK task to two
    # source calls. Reject all collisions; never choose by timestamp or order.
    counts = Counter(
        json.dumps(proof['native'], sort_keys=True) for proof in proofs
        if proof['status'] == 'verified_task_identity')
    for proof in proofs:
        if (proof['status'] == 'verified_task_identity'
                and counts[json.dumps(proof['native'], sort_keys=True)] != 1):
            proof['status'] = 'ambiguous'
            proof[
                'reason'] = 'multiple source receipts name the same native SDK task'
    token_counts = Counter(
        (receipt.get('session_id'), receipt.get('capture_epoch'),
         receipt.get('token_id')) for receipt in document.get('receipts', []))
    for proof in proofs:
        if token_counts[(proof['session_id'], proof['capture_epoch'],
                         proof['token_id'])] != 1:
            proof['status'] = 'ambiguous'
            proof[
                'reason'] = 'duplicate retained launch token in receipt artifact'
    return {
        'schema_version':
        1,
        'producer':
        'cann_native_worker_connection_tables_v1',
        'receipt_file':
        str(receipt_path),
        'receipt_sha256':
        receipt_digest,
        'raw_inputs':
        inputs,
        'capture_root':
        str(root),
        'sealed_capture_ids':
        sorted(sealed_capture_ids),
        'native_task_candidates':
        native,
        'raw_native_task_inventory':
        inventory,
        'task_identity_proofs':
        proofs,
        'clock_status':
        'unverified',
        'limits': [
            'SDK task lifecycle is a whole-task envelope, not per-program actor occupancy.',
            'Actual raw SYS counter anchors and logger counter-domain provenance are required for clock alignment.'
        ]
    }
