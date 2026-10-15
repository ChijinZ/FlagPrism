"""Calibrate local source durations from verified CANN counter provenance.

A known counter rate does not establish a shared counter epoch. This producer
never overlays actors or assigns an absolute timestamp to source observations.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

from .cann_joint import build_native_task_proofs
from .cann_raw_sys import _analysis_directory

_OFFICIAL_RATE_HZ = 50_000_000
_RATE_DOCUMENT = (
    'https://www.hiascend.com/document/detail/en/'
    'CANNCommunityEdition/910/API/ascendcopapi/docs/en/api/'
    'SIMD-API/basic_api/tool_interface/system_resources_and_variables/'
    'GetSystemCycle_ISASI.md')
_GETTER_HEADER = 'aarch64-linux/asc/impl/basic_api/dav_c220/kernel_operator_sys_var_impl.h'
_MOV = re.compile(r'MOV\s+[^,\n]+,\s*SYS_CNT')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _one(rows, reason):
    if len(rows) != 1:
        raise ValueError(reason)
    return rows[0]


def _compiled_logger(binary, actor_slot):
    metadata = binary.get('compiler_metadata') or {}
    if not re.fullmatch(r'Ascend910B[0-9-]*', str(metadata.get('arch', ''))):
        raise ValueError(
            'source target is not a supported Ascend A2/c220 target')
    handoff = metadata.get('flagprism_ascend_handoff') or {}
    if handoff.get('phase') != 'finished' or handoff.get('returncode') != 0:
        raise ValueError('source compiler handoff did not finish successfully')
    candidates = []
    expected_actor = {0: 'AIC', 1: 'AIV', 2: 'AIV'}.get(actor_slot)
    for artifact in handoff.get('artifacts', []):
        job = artifact.get('driver_job') or {}
        adapted = artifact.get('adapted') or {}
        actor = job.get('actor_kind')
        if (job.get('exit_code') != 0 or job.get('state') != 'finished'
                or actor != expected_actor
                or not str(job.get('target_arch', '')).startswith('dav-c220')
                or adapted.get('representation')
                != 'instrumented_llvm_compiled_by_sdk'):
            continue
        text = adapted.get('llir')
        if not isinstance(text, str) or not _MOV.search(text):
            continue
        digest = _sha(text.encode())
        if digest != adapted.get('sha256'):
            raise ValueError('compiled source LLVM text SHA256 differs')
        raw = Path(adapted['path']).read_bytes()
        if _sha(raw) != digest:
            raise ValueError(
                'actual compiled source LLVM bytes SHA256 differs')
        peer = _one([
            entry for entry in job.get('inputs', [])
            if entry.get('adapted_path') == adapted['path']
        ], 'source LLVM driver input missing or ambiguous')
        if peer.get('adapted_sha256') != digest or peer.get(
                'pass_returncode') != 0:
            raise ValueError(
                'source LLVM driver receipt does not bind adapted bytes')
        clock = artifact.get('metadata', {}).get('dynamic_clock', {})
        if clock.get('domain') != 'ascend.SYS_CNT':
            raise ValueError(
                'compiled source logger has an unknown counter domain')
        candidates.append({
            'adapted_path': adapted['path'],
            'adapted_sha256': digest,
            'compile_id': handoff.get('compile_id'),
            'actor_kind': actor,
            'actor_slot': actor_slot,
            'target_arch': job['target_arch'],
            'instruction': 'MOV SYS_CNT'
        })
    return _one(candidates,
                'compiled actor logger evidence is missing or ambiguous')


def _local_rate(proof, root):
    device = proof['worker']['device_id']
    path = root / proof['native']['capture_id'] / ('device_%d/info.json.%d' %
                                                   (device, device))
    raw = path.read_bytes()
    info = json.loads(raw)
    if info != proof['sdk_capture_binding_evidence'].get(
            'device_info_snapshot'):
        raise ValueError('SDK device metadata differs from lifetime seal')
    row = _one([
        entry
        for entry in info.get('DeviceInfo', []) if entry.get('id') == device
    ], 'exact SDK device metadata is missing or ambiguous')
    try:
        mhz = Decimal(str(row['hwts_frequency']))
    except (KeyError, InvalidOperation):
        raise ValueError('SDK HWTS frequency is missing or invalid') from None
    if not mhz.is_finite() or mhz * 1_000_000 != _OFFICIAL_RATE_HZ:
        raise ValueError(
            'actual SDK HWTS rate differs from documented A2 system counter rate'
        )
    analysis = _analysis_directory(None)
    header = analysis.parents[3] / _GETTER_HEADER
    source = header.read_bytes()
    text = source.decode()
    getter = re.search(r'GetSystemCycleImpl\s*\(\)\s*\{(.+?)\n\}', text,
                       re.DOTALL)
    if getter is None or not _MOV.search(getter.group(1)):
        raise ValueError(
            'installed c220 system-cycle implementation does not read SYS_CNT')
    return float(Decimal(1000) / mhz), {
        'kind':
        'exact_sdk_device_and_compiled_sys_cnt_rate_v1',
        'sdk_device_info_path':
        str(path),
        'sdk_device_info_sha256':
        _sha(raw),
        'reported_hwts_frequency_mhz':
        str(row['hwts_frequency']),
        'documented_counter_rate_hz':
        _OFFICIAL_RATE_HZ,
        'official_rate_reference':
        _RATE_DOCUMENT,
        'installed_system_cycle_header':
        str(header),
        'installed_system_cycle_header_sha256':
        _sha(source),
        'counter_instruction':
        'MOV SYS_CNT',
        'clock_epoch_status':
        'unverified',
        'semantics':
        'PIPE_S source-control duration; not engine busy or cross-actor placement'
    }


def calibrate_source_durations(observation_doc, vendor_document, task_proof):
    """Return a copy, adding only locally calibrated durations with file proof."""
    result = deepcopy(observation_doc)
    try:
        actual = build_native_task_proofs(task_proof['capture_root'],
                                          task_proof['receipt_file'])
        if actual['receipt_sha256'] != task_proof.get('receipt_sha256'):
            raise ValueError('retained receipt SHA256 differs from task proof')
        if actual['raw_inputs'] != task_proof.get('raw_inputs'):
            raise ValueError(
                'SDK raw metadata SHA256 inventory differs from task proof')
        root = Path(actual['capture_root']).resolve()
        common_error = None
    except (OSError, ValueError, KeyError, TypeError) as error:
        actual = {'task_identity_proofs': []}
        common_error = str(error)
    logger_cache = {}
    rate_cache = {}
    for event in result.get('observations', []):
        if event.get('source') != 'ascend_llvm_dynamic64':
            continue
        existing_clock = event.get('clock') or {}
        if (existing_clock.get('domain') != 'ascend.SYS_CNT'
                or existing_clock.get('scope') != 'actor_local'
                or existing_clock.get('alignment')
                not in ('instance_local', 'unverified')):
            # Preserve independently established clocks and unrelated domains.
            continue
        try:
            if common_error is not None:
                raise ValueError(common_error)
            association = event.get('association_evidence') or {}
            invocation, binary_id = event.get(
                'invocation_id'), association.get('binary_id')
            if (event.get('association_status') != 'verified'
                    or association.get('invocation_id') != invocation
                    or not binary_id):
                raise ValueError(
                    'source event has no exact invocation and binary identity')
            proof = _one([
                entry for entry in actual['task_identity_proofs']
                if entry.get('invocation_id') == invocation
            ], 'recomputed native source proof is missing or ambiguous')
            declared = _one([
                entry for entry in task_proof.get('task_identity_proofs', [])
                if entry.get('invocation_id') == invocation
            ], 'declared native source proof is missing or ambiguous')
            if (proof != declared
                    or proof.get('status') != 'verified_task_identity'
                    or proof.get('binary_id') != binary_id
                    or proof.get('scope_id') != association.get('scope_id')):
                raise ValueError(
                    'native source proof differs from independently revalidated files'
                )
            row = _one([
                entry for entry in vendor_document.get('associations', [])
                if entry.get('source') == 'cann_sdk_task'
                and isinstance(entry.get('invocation_identity'), dict) and
                entry['invocation_identity'].get('invocation_id') == invocation
            ], 'canonical native source row is missing or ambiguous')
            identity = row['invocation_identity']
            if (identity.get('status') != 'verified_task_identity' or any(
                    identity.get(key) != proof.get(key)
                    for key in ('invocation_id', 'binary_id', 'scope_id',
                                'session_id', 'capture_epoch', 'token_id'))
                    or row.get('metrics', {}).get('sdk_task')
                    != proof['native']['sdk_task']):
                raise ValueError(
                    'canonical native task does not match recomputed source proof'
                )
            binary = _one([
                entry for entry in vendor_document.get('binaries', [])
                if entry.get('id') == binary_id
            ], 'source binary is missing or ambiguous')
            logger_key = (binary_id, event.get('actor_slot'))
            if logger_key not in logger_cache:
                logger_cache[logger_key] = _compiled_logger(
                    binary, event.get('actor_slot'))
            logger = logger_cache[logger_key]
            rate_key = (proof['native']['capture_id'],
                        proof['worker']['device_id'])
            if rate_key not in rate_cache:
                rate_cache[rate_key] = _local_rate(proof, root)
            period, evidence = rate_cache[rate_key]
            evidence = deepcopy(evidence)
            clock = event.get('clock') or {}
            if (clock.get('domain') != 'ascend.SYS_CNT'
                    or clock.get('scope') != 'actor_local'
                    or clock.get('alignment')
                    not in ('instance_local', 'unverified')):
                raise ValueError(
                    'source event has an unsupported clock domain or scope')
            start, end = event.get('start_tick'), event.get('end_tick')
            if type(start) is not int or type(
                    end) is not int or not 0 <= start <= end < 2**64:
                raise ValueError(
                    'source duration requires monotone unsigned counter values'
                )
            evidence.update(compiled_logger=logger,
                            receipt_sha256=actual['receipt_sha256'],
                            invocation_id=invocation,
                            binary_id=binary_id)
            # Rate evidence supplies no common epoch, even if caller metadata did.
            event['clock'] = dict(clock,
                                  tick_ns=period,
                                  conversion_evidence=evidence)
            for key in ('origin_tick', 'origin_ns', 'alignment_evidence'):
                event['clock'].pop(key, None)
            event['duration_ns'] = (end - start) * period
            event['relative_start_ns'] = None
            event.pop('conversion_rejection_reason', None)
        except (OSError, ValueError, KeyError, TypeError) as error:
            event['conversion_rejection_reason'] = str(error)
            event['duration_ns'] = None
            event['relative_start_ns'] = None
            if isinstance(event.get('clock'), dict):
                event['clock']['tick_ns'] = None
    return result
