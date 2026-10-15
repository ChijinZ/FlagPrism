"""Recover original CANN task SYS counts without certifying clock alignment.

Identity comes first from retained worker tokens and SDK connection tables. Raw
ACSQ records supply a whole-task envelope only; they do not measure actor busy
intervals and cannot establish that source logger clocks share an offset.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

from .cann_joint import build_native_task_proofs

_SCHEMA_FILES = (
    'msparser/data_struct_size_constant.py',
    'profiling_bean/struct_info/struct_decoder.py',
    'profiling_bean/stars/acsq_task.py',
    'msparser/stars/stars_log_parser.py',
    'profiling_bean/stars/stars_common.py',
    'common_func/file_name_manager.py',
)
_ANALYSIS_SUFFIX = 'tools/profiler/profiler_tool/analysis'


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _analysis_directory(analysis_root):
    if analysis_root is not None:
        return Path(analysis_root).resolve()
    configured = [
        os.environ.get(key)
        for key in ('ASCEND_HOME_PATH', 'ASCEND_TOOLKIT_HOME',
                    'ASCEND_INSTALL_PATH')
    ]
    candidates = configured + [
        '/usr/local/Ascend/ascend-toolkit/latest', '/usr/local/Ascend/latest',
        '/usr/local/Ascend/cann-9.0.0'
    ]
    discovered = set()
    for value in candidates:
        if value:
            candidate = (Path(value) / _ANALYSIS_SUFFIX).resolve()
            if (candidate / _SCHEMA_FILES[0]).is_file():
                discovered.add(candidate)
    if len(discovered) != 1:
        raise ValueError(
            'installed CANN analysis schema is missing or ambiguous')
    return discovered.pop()


def _schema(analysis_root):
    root = _analysis_directory(analysis_root)
    sources = {}
    for name in _SCHEMA_FILES:
        path = root / name
        if not path.is_file():
            raise ValueError('installed CANN analysis schema is incomplete')
        raw = path.read_bytes()
        sources[name] = {'path': str(root / name), 'sha256': _digest(raw)}
    tree = ast.parse((root / _SCHEMA_FILES[0]).read_text())
    constants = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value,
                                                       ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = node.value.value
    if (constants.get('BYTE_ORDER_CHAR') != '='
            or constants.get('ACSQ_TASK_FMT') != '4HQHH11L'
            or struct.calcsize('=4HQHH11L') != 64):
        raise ValueError('unsupported installed CANN ACSQ schema')
    if sys.byteorder != 'little':
        raise ValueError(
            'CANN raw SYS producer requires verified little endian host')
    return {
        'format': '=4HQHH11L',
        'size': 64,
        'sources': sources,
        'analysis_root': str(root)
    }


def _decode_records(raw, provenance):
    """Decode SDK's 64-byte records; reject encodings we cannot certify."""
    if len(raw) % 64:
        raise ValueError('truncated CANN STARS record file')
    decoded = []
    for offset in range(0, len(raw), 64):
        payload = raw[offset:offset + 64]
        func_type = payload[0] & 63
        # The initial producer deliberately declines mixed 128-byte PMU logs.
        # Their trailing halves must never be mistaken for ACSQ task headers.
        if func_type in (40, 41):
            raise ValueError(
                '128-byte STARS PMU records require a separate decoder')
        if func_type not in (0, 1):
            continue
        fields = struct.unpack('=4HQHH11L', payload)
        stream, task = fields[2:4]
        if stream >= 4096 or task >= 4096:
            raise ValueError(
                'expanded STARS stream/task encoding is unsupported')
        decoded.append(
            dict(provenance,
                 byte_offset=offset,
                 raw_record_hex=payload.hex(),
                 raw_record_sha256=_digest(payload),
                 function_type=func_type,
                 stream_id=stream,
                 task_id=task,
                 raw_sys_counter=fields[4]))
    return decoded


def build_raw_task_sys(capture_root, receipt_file, analysis_root=None):
    """Rebuild exact task proof from files, then extract unique raw endpoints.

    Caller-provided proof dictionaries, timestamps and task-name matching are
    intentionally absent. Unsupported schemas/files remain explicit failures;
    successful extraction still leaves all cross-clock alignment unverified.
    """
    schema = _schema(analysis_root)
    proofs = build_native_task_proofs(capture_root, receipt_file)
    root = Path(capture_root).resolve()
    files = []
    results = []
    for proof in proofs['task_identity_proofs']:
        result = {
            key: proof.get(key)
            for key in ('invocation_id', 'binary_id', 'session_id',
                        'capture_epoch', 'scope_id')
        }
        result.update(status='unassociated',
                      clock_alignment='unverified',
                      reason='exact SDK task identity is unavailable')
        if proof['status'] != 'verified_task_identity':
            results.append(result)
            continue
        capture = root / proof['native']['capture_id']
        worker = proof['worker']
        info = json.loads(
            (capture /
             ('device_%d/info.json.%d' %
              (worker['device_id'], worker['device_id']))).read_text())
        devices = [
            entry for entry in info.get('DeviceInfo', [])
            if entry.get('id') == worker['device_id']
        ]
        if (str(info.get('platform_version')) != '5' or len(devices) != 1
                or devices[0].get('ctrl_cpu_endian_little') != 1):
            result[
                'reason'] = 'unsupported SDK platform or device endian evidence'
            results.append(result)
            continue
        records = []
        try:
            paths = sorted((capture / ('device_%d/data' % worker['device_id'])
                            ).glob('stars_soc.data.*.slice_*'))
            for path in paths:
                if not path.is_file() or path.name.endswith('.done'):
                    continue
                raw = path.read_bytes()
                evidence = {
                    'path': str(path.relative_to(root)),
                    'sha256': _digest(raw),
                    'bytes': len(raw)
                }
                if evidence not in files:
                    files.append(evidence)
                records.extend(_decode_records(raw, evidence))
            selected = [
                entry for entry in records
                if entry['stream_id'] == worker['stream_id']
                and entry['task_id'] == worker['task_id']
            ]
            starts = [
                entry for entry in selected if entry['function_type'] == 0
            ]
            ends = [entry for entry in selected if entry['function_type'] == 1]
            if len(starts) != 1 or len(ends) != 1:
                result.update(
                    reason='raw task endpoint is missing or ambiguous',
                    start_count=len(starts),
                    end_count=len(ends))
            elif ends[0]['raw_sys_counter'] < starts[0]['raw_sys_counter']:
                result['reason'] = 'raw task SYS counter reverses or wraps'
            else:
                result.update(status='raw_task_envelope_extracted',
                              reason=None,
                              native_identity=proof['native'],
                              start=starts[0],
                              end=ends[0],
                              evidence_kind='sealed_sdk_task_and_raw_acsq_sys')
        except ValueError as error:
            result['reason'] = str(error)
        results.append(result)
    return {
        'schema_version':
        1,
        'producer':
        'cann_raw_acsq_sys_v1',
        'clock_status':
        'unverified',
        'schema':
        schema,
        'receipt_sha256':
        proofs['receipt_sha256'],
        'raw_inputs':
        files,
        'task_sys_envelopes':
        results,
        'limits': [
            'Whole SDK task envelopes are not per-actor occupancy.',
            'Source logger counter-domain and offset evidence remain required.'
        ]
    }
