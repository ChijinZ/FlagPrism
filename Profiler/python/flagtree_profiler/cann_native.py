"""Exact CANN TASK inventory and retained-worker source associations.

SDK task timestamps describe whole-task lifecycles. They do not establish a
clock conversion for independently recorded actor intervals.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

_PRODUCER = 'cann_native_worker_connection_tables_v1'
_EVIDENCE = 'retained_worker_token_and_sdk_connection_tables'
_KERNEL_TYPES = {
    'KERNEL_AICORE': 'AI_CORE',
    'KERNEL_AIVEC': 'AI_VECTOR_CORE',
    'KERNEL_MIX_AIC': 'MIX_AIC',
    'KERNEL_MIX_AIV': 'MIX_AIV',
    'KERNEL_AICPU': 'AI_CPU'
}
_TYPE_SOURCE = {
    'sdk': 'CANN 9.0.0',
    'path':
    'tools/profiler/profiler_tool/analysis/mscalculate/cann/cann_analysis_gear.py',
    'sha256':
    'be465c67c17b9f666f19f8ac8a7a43a6123cd6387c27f7a2611d54f498904be5',
    'table': 'RTS_TASK_TYPE_MAP'
}


def _uint(value):
    return type(value) is int and 0 <= value < 2**64


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def _capture_path(root, capture_id):
    if not isinstance(capture_id, str) or not capture_id:
        return None
    relative = Path(capture_id)
    if relative.is_absolute() or '..' in relative.parts:
        return None
    path = (root / relative).resolve()
    return path if path == root or root in path.parents else None


def _context_valid(entry):
    """Validate the SDK's explicit HostTask context membership, when present."""
    task, host = entry['sdk_task'], entry['sdk_host_task']
    if 'context_ids' not in host and 'context_join' not in entry:
        return True  # Older single-task SDK fixtures have no context columns.
    raw = host.get('context_ids')
    if not isinstance(raw, str) or not raw:
        return False
    parts = [part.strip() for part in raw.split(',')]
    if any(not part.isascii() or not part.isdecimal() for part in parts):
        return False
    contexts = [int(part) for part in parts]
    if len(set(contexts)) != len(contexts) or any(value >= 2**32
                                                  for value in contexts):
        return False
    context = task.get('contextId')
    expected = {
        'kind': 'sdk_host_context_membership_v1',
        'task_context_id': context,
        'host_context_ids': contexts,
        'model_id': task.get('modelId')
    }
    return (_uint(context) and context < 2**32 and context in contexts
            and entry.get('context_join') == expected
            and (('model_id' not in host and 'modelId' not in task) or
                 (_uint(task.get('modelId')) and _uint(host.get('model_id'))
                  and host['model_id'] == task['modelId'])))


def _dispatch_family(entry):
    task, host = entry['sdk_task'], entry['sdk_host_task']
    return (entry.get('capture_id'), task['globalPid'], task['deviceId'],
            task['streamId'], task['taskId'], task['connectionId'],
            task.get('modelId'), host.get('batch_id'), host['thread_id'])


def _compute_valid(entry, inventory):
    info = entry.get('sdk_compute_task_info')
    if not isinstance(info, dict) or not _uint(info.get('globalTaskId')):
        return False
    matches = [
        row for row in inventory
        if isinstance(row, dict) and row.get('capture_id') ==
        entry['capture_id'] and isinstance(row.get(
            'sdk_compute_task_info'), dict) and row['sdk_compute_task_info'].
        get('globalTaskId') == entry['sdk_task'].get('globalTaskId')
    ]
    return (info['globalTaskId'] == entry['sdk_task'].get('globalTaskId')
            and len(matches) == 1
            and matches[0]['sdk_compute_task_info'] == info)


def _candidate_valid(entry):
    if not isinstance(entry, dict):
        return False
    task, host = entry.get('sdk_task'), entry.get('sdk_host_task')
    if not isinstance(task, dict) or not isinstance(host, dict):
        return False
    if not all(
            _uint(task.get(k)) for k in ('globalPid', 'deviceId', 'streamId',
                                         'taskId', 'connectionId', 'startNs',
                                         'endNs')) or task['globalPid'] == 0:
        return False
    return (_context_valid(entry) and task['endNs'] >= task['startNs']
            and type(host.get('thread_id')) is int and host['thread_id'] > 0
            and all(
                host.get(left) == task[right] and _uint(host.get(left))
                for left, right in (('device_id', 'deviceId'),
                                    ('stream_id', 'streamId'),
                                    ('task_id', 'taskId'),
                                    ('connection_id', 'connectionId'))))


def _verify_dispatch(item, entry, candidates, inventory, compute_inventory):
    """Recheck all same-dispatch context views before source attribution."""
    family = _dispatch_family(entry)
    views = [
        view for view in candidates
        if _candidate_valid(view) and _dispatch_family(view) == family
    ]
    contextual = any('context_join' in view for view in views)
    evidence = item.get('dispatch_context_evidence')
    task = entry['sdk_task']
    key = dict(
        zip(('capture_id', 'process_id', 'device_id', 'stream_id', 'task_id',
             'connection_id', 'model_id', 'batch_id', 'worker_thread_id'),
            family))
    members = [
        view for view in views if _compute_valid(view, compute_inventory)
    ]
    raw_views = [
        row for row in inventory
        if isinstance(row, dict) and row.get('capture_id') ==
        entry['capture_id'] and isinstance(row.get('sdk_task'), dict) and all(
            row['sdk_task'].get(field) == task.get(field)
            for field in ('globalPid', 'deviceId', 'streamId', 'taskId',
                          'connectionId', 'modelId'))
    ]
    if ({_key(row['sdk_task'])
         for row in raw_views} != {_key(view['sdk_task'])
                                   for view in views}):
        return 'dispatch context views do not cover the complete SDK TASK inventory'
    if not contextual and len(views) == 1:
        return None
    if (len(views) == 1 and entry.get('compute_membership') == 'unavailable'
            and not any(
                row.get('capture_id') == entry['capture_id']
                for row in compute_inventory if isinstance(row, dict))):
        return None
    if (not isinstance(evidence, dict) or evidence.get('kind')
            != 'sdk_context_membership_and_compute_global_task_id_v1'
            or evidence.get('dispatch_key') != key
            or not isinstance(evidence.get('all_context_views'), list)
            or sorted(_key(view)
                      for view in evidence['all_context_views']) != sorted(
                          _key(view) for view in views)):
        return 'dispatch context evidence differs from complete native candidates'
    if (len(members) != 1 or evidence.get('compute_member_count') != 1
            or members[0] != entry
            or evidence.get('selected_compute_global_task_id')
            != task.get('globalTaskId')):
        return 'compound or unverified compute membership cannot bind one source invocation'
    return None


def _kernel_task(entry):
    # Exact installed SDK enums; TASK.taskType is a separate opaque enum.
    return entry['sdk_host_task'].get('task_type') in _KERNEL_TYPES


def _load_receipts(proof):
    try:
        raw = Path(proof['receipt_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != proof.get('receipt_sha256'):
            return [], 'retained receipt SHA256 does not match'
        artifact = json.loads(raw)
        if artifact.get('schema_version') != 1 or not isinstance(
                artifact.get('receipts'), list):
            return [], 'invalid retained receipt artifact'
        return artifact['receipts'], None
    except (OSError, ValueError, KeyError, TypeError):
        return [], 'retained receipt artifact unavailable or malformed'


def _verify_source(item, entry, receipts, launches, binaries, root):
    """Recheck raw receipt ownership; a serialized status is insufficient."""
    if item.get('status') != 'verified_task_identity' or item.get(
            'evidence_kind') != _EVIDENCE:
        return None, 'no verified retained worker proof'
    if not all(
            _uint(item.get(k))
            for k in ('scope_id', 'session_id', 'token_id',
                      'capture_epoch')) or not item['capture_epoch']:
        return None, 'invalid retained token/session/epoch identity'
    matches = [
        r for r in receipts if isinstance(r, dict) and all(
            r.get(k) == item[k]
            for k in ('session_id', 'capture_epoch', 'token_id'))
    ]
    if len(matches) != 1:
        return None, 'retained token/session/epoch missing or ambiguous'
    receipt = matches[0]
    worker = item.get('worker')
    from .cann_joint import _worker_is_valid, _sealed_capture
    if not _worker_is_valid(receipt) or worker != receipt.get('worker'):
        return None, 'retained worker identity or query status differs'
    try:
        sealed = _sealed_capture(receipt, [], root)
        evidence = json.loads(
            receipt.get('sdk_capture_binding_evidence') or 'null')
    except (OSError, ValueError, TypeError, KeyError):
        return None, 'SDK lifetime seal cannot be revalidated'
    if (sealed != entry['capture_id']
            or evidence != item.get('sdk_capture_binding_evidence')):
        return None, 'SDK capture/epoch seal differs from retained receipt'
    identity = receipt.get('invocation_identity')
    if (not isinstance(identity, dict)
            or identity.get('evidence') != 'retained_per_launch_worker_receipt'
            or any(
                identity.get(k) != item.get(k)
                for k in ('scope_id', 'session_id', 'invocation_id',
                          'binary_id'))
            or receipt.get('scope_id') != item['scope_id']):
        return None, 'retained source invocation identity differs'
    task, host = entry['sdk_task'], entry['sdk_host_task']
    if any(task[k] != worker.get(v) for k, v in (
        ('globalPid', 'process_id'), ('deviceId', 'device_id'),
        ('streamId', 'stream_id'),
        ('taskId',
         'task_id'))) or host['thread_id'] != worker.get('thread_id'):
        return None, 'native TASK/HostTask and retained worker tuple differ'
    peers = [
        launch for launch in launches if isinstance(launch, dict)
        and launch.get('id') == item.get('invocation_id')
    ]
    binary_peers = [
        binary for binary in binaries if isinstance(binary, dict)
        and binary.get('id') == item.get('binary_id')
    ]
    if len(peers) != 1 or len(binary_peers) != 1:
        return None, 'launch or binary identity missing or ambiguous'
    launch = peers[0]
    if (launch.get('status') == 'rejected_before_launch'
            or launch.get('binary_id') != item.get('binary_id')
            or launch.get('scope_id') != item['scope_id']
            or not isinstance(launch.get('arguments'), dict)
            or ('session_id' in launch
                and launch['session_id'] != item['session_id'])):
        return None, 'actual source launch does not match retained identity'
    return {
        k: item[k]
        for k in ('invocation_id', 'binary_id', 'scope_id', 'session_id',
                  'token_id', 'capture_epoch')
    } | {
        'status': 'verified_task_identity',
        'evidence_kind': _EVIDENCE
    }, None


def _native_row(entry, identity, reason, receipt_sha256):
    task, host = entry['sdk_task'], entry['sdk_host_task']
    scope = identity['scope_id'] if identity else None
    context = task.get('contextId')
    if not _uint(context) or context == 2**32 - 1:
        context = None
    metrics = {
        'activity.kind':
        'kernel',
        'activity.process_id':
        task['globalPid'],
        'activity.thread_id':
        host['thread_id'],
        'activity.context_id':
        context,
        'activity.device_id':
        task['deviceId'],
        'activity.stream_id':
        task['streamId'],
        'activity.task_id':
        task['taskId'],
        'activity.correlation_id':
        task['connectionId'],
        'activity.scope_id':
        scope,
        'activity.capture_id':
        entry['capture_id'],
        'activity.global_task_id':
        task.get('globalTaskId'),
        'activity.clock_domain':
        'cann_sdk_export',
        'activity.clock_alignment':
        'unverified',
        'activity.correlation_domain':
        'cann.sdk.connection:' + entry['capture_id'],
        'activity.semantics':
        'native_device_task_lifecycle',
        'activity.duration_scope':
        'whole_task_lifecycle_not_actor_occupancy',
        'activity.task_class':
        _KERNEL_TYPES[host['task_type']],
        'activity.association':
        'verified_task_identity' if identity else 'unassociated',
        'activity.association_reason':
        reason,
        'activity.receipt_sha256':
        receipt_sha256,
        'activity.unknown_fields':
        ','.join(k for k, v in (('scope_id', scope), ('context_id', context))
                 if v is None),
        'sdk_task':
        deepcopy(task),
        'sdk_host_task':
        deepcopy(host),
        'sdk_compute_task_info':
        deepcopy(entry.get('sdk_compute_task_info')),
        'sdk_context_join':
        deepcopy(entry.get('context_join'))
    }
    return {
        'source':
        'cann_sdk_task',
        'state':
        'collected',
        'metrics':
        metrics,
        'runtime_event': {
            'op_name': host.get('kernel_name') or None,
            'device_id': task['deviceId'],
            'stream_id': task['streamId'],
            'task_id': task['taskId'],
            'correlation_id': task['connectionId'],
            'scope_id': scope,
            'start_time_ns': task['startNs'],
            'end_time_ns': task['endNs']
        },
        'invocation_identity':
        identity,
        'note':
        'SDK whole-task lifecycle; independent actor/SYS clock alignment is unverified.'
    }


def _legacy_match(row,
                  inventory,
                  canonical,
                  root,
                  sealed,
                  *,
                  return_matches=False):
    """Only exact capture/declared IDs may supersede an older export view."""
    if row.get('source') not in ('aclprof_op_summary', 'msprof_native_trace'):
        return None
    metrics, raw = row.get('metrics', {}), row.get('runtime_event', {})
    if (metrics.get('activity.kind') != 'kernel'
            or row.get('state') != 'collected' or not isinstance(raw, dict)):
        return None
    unknown = metrics.get('activity.unknown_fields', '')
    if not isinstance(unknown, str):
        return None
    unknown = {
        value.strip().removeprefix('activity.')
        for value in unknown.split(',')
    }
    source = metrics.get('input_file')
    if not isinstance(source, str) or not Path(source).is_absolute():
        return None
    path = Path(source).resolve()
    if not path.is_file():
        return None
    captures = [
        capture for capture in sealed
        if (owned := _capture_path(root, capture)) is not None
        and owned in path.parents
    ]
    if len(captures) != 1:
        return None
    values = {}
    for name, field in (('device_id', 'deviceId'), ('stream_id', 'streamId'),
                        ('task_id', 'taskId')):
        if name in unknown:
            return None
        value = raw.get(name)
        if not _uint(value):
            return None
        # The old runtime envelope can contain dummy zeros. Require a declared
        # summary field or the native trace's actual SDK argument tuple.
        declarations = [
            metrics[key] for key in (name, 'activity.' + name)
            if key in metrics
        ]
        if not declarations and row['source'] == 'msprof_native_trace':
            try:
                trace = json.loads(metrics.get('raw_event_json', 'null'))
                args = trace.get('args', {})
                declarations = [{
                    'device_id': value,
                    'stream_id': args.get('Physic Stream Id'),
                    'task_id': args.get('Task Id')
                }[name]]
            except (ValueError, TypeError, AttributeError):
                return None
        if not declarations or any(not _uint(declared) or declared != value
                                   for declared in declarations):
            return None
        values[field] = value
    for field, name, aliases in (('globalPid', 'process_id',
                                  ('process_id', 'activity.process_id')),
                                 ('connectionId', 'correlation_id',
                                  ('connection_id', 'correlation_id',
                                   'activity.correlation_id')),
                                 ('contextId', 'context_id',
                                  ('context_id', 'activity.context_id')),
                                 ('globalTaskId', 'global_task_id',
                                  ('global_task_id',
                                   'activity.global_task_id'))):
        if name in unknown:
            continue
        for key in aliases:
            value = metrics.get(key)
            # Untyped CSV columns such as context_id='N/A' are unavailable.
            # Explicit typed activity identities must be numeric if supplied.
            if value is None or (not key.startswith('activity.')
                                 and type(value) is not int):
                continue
            if not _uint(value):
                return None
            if field in values and values[field] != value:
                return None
            values[field] = value
    # Positive legacy correlation IDs are actual declarations; zero needs an
    # explicit typed metric and must not be inferred from envelope storage.
    correlation = raw.get('correlation_id')
    if 'correlation_id' not in unknown and _uint(
            correlation) and correlation > 0:
        if 'connectionId' in values and values['connectionId'] != correlation:
            return None
        values['connectionId'] = correlation
    matches = [
        entry for entry in inventory
        if isinstance(entry, dict) and entry.get('capture_id') == captures[0]
        and isinstance(entry.get('sdk_task'), dict) and all(
            entry['sdk_task'].get(k) == value for k, value in values.items())
    ]
    unique = {_key(entry): entry for entry in matches}
    if return_matches:
        return list(unique.values())
    if len(unique) != 1:
        return None
    selected = next(iter(unique.values()))
    peers = [
        index for index, entry in enumerate(canonical)
        if entry['capture_id'] == selected['capture_id']
        and entry['sdk_task'] == selected['sdk_task']
    ]
    return peers[0] if len(peers) == 1 else None


def normalize_legacy_activity_kinds(document):
    """Classify SDK export rows by exact Task Type, independently of source proof.

    Profiler markers and device event records remain raw extensions. Their
    intervals never contribute to kernel counts, busy time or kernel hotspots.
    """
    result = deepcopy(document)
    if result.get('backend') != 'cann':
        return result
    previous = {
        row['original_index']: row
        for row in result.get('cann_native_activity_extensions', [])
        if isinstance(row, dict) and 'original_index' in row
    }
    extensions, counts = [], Counter()
    kernel_types = set(_KERNEL_TYPES) | set(_KERNEL_TYPES.values())
    for index, row in enumerate(result.get('associations', [])):
        if row.get('source') not in ('msprof_native_trace',
                                     'aclprof_op_summary'):
            continue
        metrics = row.get('metrics', {})
        old_kind = metrics.get('activity.kind')
        args = None
        if 'raw_event_json' in metrics:
            try:
                payload = json.loads(metrics['raw_event_json'])
                args = payload.get('args', {}) if isinstance(payload,
                                                             dict) else None
            except (ValueError, TypeError):
                pass
        task_type = args.get('Task Type') if isinstance(
            args, dict) else metrics.get('task_type')
        if task_type is None and old_kind != 'kernel':
            continue  # Host runtime API rows need no device Task Type.
        original = deepcopy(previous.get(index, {}).get('original_row', row))
        if isinstance(task_type, str) and task_type in kernel_types:
            kind, reason = 'kernel', 'explicit SDK kernel Task Type'
        elif task_type == 'PCIE_DMA_SQE':
            kind, reason = 'memcpy', 'explicit SDK DMA Task Type'
            size = args.get('size(B)') if isinstance(args, dict) else None
            metrics['activity.bytes'] = size if _uint(size) else None
            operation = args.get('operation') if isinstance(args,
                                                            dict) else None
            metrics['activity.copy_operation'] = operation
            metrics['activity.copy_direction'] = {
                'device to host': 'device_to_host',
                'host to device': 'host_to_device',
                'device to device': 'device_to_device',
                'host to host': 'host_to_host'
            }.get(operation) if isinstance(operation, str) else None
        elif task_type == 'PROFILER_TRACE_EX':
            kind, reason = 'profiler_marker', 'SDK profiler trace marker, not kernel execution'
        elif task_type == 'EVENT_RECORD':
            kind, reason = 'device_event_record', 'SDK device event record, not kernel execution'
        else:
            kind, reason = 'unclassified_device_task', 'SDK Task Type is missing, malformed or not in the explicit kernel/category map'
        metrics.setdefault('activity.original_kind', old_kind)
        metrics['activity.kind'] = kind
        metrics['activity.sdk_task_type'] = task_type
        metrics['activity.classification_reason'] = reason
        metrics.setdefault('activity.clock_alignment', 'unverified')
        if kind != 'kernel':
            metrics['activity.association'] = 'unassociated'
            metrics['activity.association_reason'] = reason
            metrics['activity.semantics'] = {
                'memcpy': 'native_device_memcpy_lifecycle',
                'profiler_marker': 'native_profiler_marker',
                'device_event_record': 'native_device_event_record',
                'unclassified_device_task': 'unclassified_native_device_task'
            }[kind]
            row.pop('invocation_identity', None)
        counts[kind] += 1
        if kind in ('profiler_marker', 'device_event_record',
                    'unclassified_device_task'):
            extensions.append({
                'original_index': index,
                'original_source': row.get('source'),
                'kind': kind,
                'task_type': task_type,
                'reason': reason,
                'original_row': original,
                'normalized_row': deepcopy(row)
            })
    result['cann_native_activity_extensions'] = extensions
    result.setdefault('capture', {})['cann_native_activity_kinds'] = {
        'counts': dict(counts),
        'classification':
        'exact SDK Task Type; no operation-name classification',
        'extension_timing': 'not included in kernel busy time or hotspots',
        'clock_alignment': 'unverified'
    }
    return result


def augment_native_tasks(document, proof):
    """Return a copy with sealed SDK TASK rows and verified source identities.

    Missing receipt bytes disable source attribution, not native row retention.
    Ambiguous old export views remain visible. Superseded rows remain auditable
    in ``cann_native_superseded_views``; caller-owned raw artifacts are untouched.
    """
    result = deepcopy(document)
    if (not isinstance(proof, dict) or proof.get('schema_version') != 1
            or proof.get('producer') != _PRODUCER
            or not isinstance(proof.get('capture_root'), str)
            or not Path(proof['capture_root']).is_absolute()):
        return result
    root = Path(proof['capture_root']).resolve()
    sealed = proof.get('sealed_capture_ids', [])
    if not isinstance(sealed, list):
        return result
    sealed = {
        value
        for value in sealed if _capture_path(root, value) is not None
    }
    candidates = proof.get('native_task_candidates', [])
    inventory = proof.get('raw_native_task_inventory', [])
    if not isinstance(candidates, list) or not isinstance(inventory, list):
        return result
    compute_inventory = proof.get('raw_compute_task_inventory', [])
    compute_inventory = compute_inventory if isinstance(
        compute_inventory, list) else []
    compute_captures = proof.get('compute_task_info_captures', [])
    compute_captures = {
        value
        for value in compute_captures if isinstance(value, str)
    } if isinstance(compute_captures, list) else set()
    compute_captures.update(
        row.get('capture_id') for row in compute_inventory
        if isinstance(row, dict) and isinstance(row.get('capture_id'), str))
    canonical, unclassified, dispatch = [], [], []
    for entry in candidates:
        if (_candidate_valid(entry) and entry.get('capture_id') in sealed
                and entry not in canonical):
            if _kernel_task(entry):
                if entry['capture_id'] in compute_captures:
                    if _compute_valid(entry, compute_inventory):
                        canonical.append(entry)
                    else:
                        dispatch.append({
                            'native':
                            deepcopy(entry),
                            'reason':
                            'SDK context has no unique consistent COMPUTE_TASK_INFO globalTaskId membership'
                        })
                else:
                    family_views = [
                        view for view in candidates if _candidate_valid(view)
                        and _dispatch_family(view) == _dispatch_family(entry)
                    ]
                    if 'context_join' in entry and len(family_views) > 1:
                        dispatch.append({
                            'native':
                            deepcopy(entry),
                            'reason':
                            'Multiple SDK context views have no verified compute membership'
                        })
                    else:
                        canonical.append(entry)
            else:
                unclassified.append({
                    'native':
                    deepcopy(entry),
                    'reason':
                    'SDK TASK/HostTask type pair is not a supported kernel classification'
                })
    receipts, receipt_error = _load_receipts(proof)
    proofs = proof.get('task_identity_proofs', [])
    proofs = proofs if isinstance(proofs, list) else []
    proof_counts = Counter(
        _key(item.get('native')) for item in proofs if isinstance(item, dict))
    invocation_counts = Counter(
        _key(item.get('invocation_id')) for item in proofs
        if isinstance(item, dict)
        and item.get('status') == 'verified_task_identity')
    rows = []
    for entry in canonical:
        peers = [
            item for item in proofs
            if isinstance(item, dict) and item.get('native') == entry
        ]
        identity, reason = None, receipt_error or 'no unique retained source proof'
        if not receipt_error and len(peers) == 1 and proof_counts[_key(
                entry)] == 1:
            item = peers[0]
            if invocation_counts[_key(item.get('invocation_id'))] == 1:
                dispatch_error = _verify_dispatch(item, entry, candidates,
                                                  inventory, compute_inventory)
                identity, reason = _verify_source(item, entry, receipts,
                                                  result.get('launches', []),
                                                  result.get('binaries', []),
                                                  root)
                if dispatch_error:
                    identity, reason = None, dispatch_error
            else:
                reason = 'multiple native tasks claim the same source invocation'
        rows.append(
            _native_row(entry, identity, reason, proof.get('receipt_sha256')))
    retained, superseded = [], []
    dispatch_extensions = deepcopy(
        result.get('cann_native_dispatch_extensions', []))
    for original_index, row in enumerate(result.get('associations', [])):
        if row.get('source') == 'cann_sdk_task' and any(
                row.get('metrics', {}).get('activity.capture_id') ==
                entry['capture_id'] and row.get('metrics', {}).get('sdk_task')
                == entry['sdk_task'] and row.get('metrics', {}).get(
                    'sdk_host_task') == entry['sdk_host_task']
                for entry in canonical):
            continue  # Re-export updates the same exact canonical inventory.
        index = _legacy_match(row, inventory, canonical, root, sealed)
        matches = _legacy_match(
            row, inventory, canonical, root, sealed,
            return_matches=True) or []
        parent_matches = [
            view for view in dispatch
            if any(view['native']['capture_id'] == match['capture_id']
                   and view['native']['sdk_task'] == match['sdk_task']
                   for match in matches)
        ]
        if index is None and parent_matches:
            original = deepcopy(row)
            ambiguous = len(matches) > 1
            kind = 'unclassified_device_task' if ambiguous else 'dispatch_context_view'
            reason = (
                'context_ambiguous: legacy view lacks a unique compute/context identity'
                if ambiguous else
                'exact SDK dispatch context view; not a compute task')
            row['metrics']['activity.kind'] = kind
            row['metrics']['activity.association'] = 'unassociated'
            row['metrics']['activity.association_reason'] = reason
            row.pop('invocation_identity', None)
            extension = {
                'original_index': original_index,
                'original_source': row.get('source'),
                'kind': kind,
                'reason': reason,
                'original_row': original,
                'normalized_row': deepcopy(row),
                'matching_native_inventory': deepcopy(matches)
            }
            if not any(
                    old.get('normalized_row') == row
                    for old in dispatch_extensions):
                dispatch_extensions.append(extension)
            retained.append(row)
        elif index is None:
            retained.append(row)
        else:
            superseded.append({
                'row': row,
                'original_index': original_index,
                'original_source': row.get('source'),
                'identity_basis':
                'exact_sealed_capture_and_unique_complete_TASK_inventory',
                'canonical_task': deepcopy(canonical[index])
            })
    result['associations'] = retained + rows
    result['cann_native_unclassified_tasks'] = unclassified
    result['cann_native_dispatch_contexts'] = dispatch
    result['cann_native_dispatch_extensions'] = dispatch_extensions
    result.setdefault('cann_native_superseded_views', []).extend(superseded)
    result.setdefault('capture', {})['cann_native_tasks'] = {
        'canonical_tasks':
        len(rows),
        'associated_tasks':
        sum(row['invocation_identity'] is not None for row in rows),
        'unclassified_tasks':
        len(unclassified),
        'dispatch_context_views':
        len(dispatch),
        'dispatch_legacy_extensions':
        len(dispatch_extensions),
        'kernel_classification_source':
        deepcopy(_TYPE_SOURCE),
        'superseded_export_views':
        len(superseded),
        'clock_alignment':
        'unverified',
        'duration_scope':
        'whole_task_lifecycle_not_actor_occupancy'
    }
    return result
