"""Decode the Ascend per actor dynamic64 log without inventing clock joins."""
from __future__ import annotations
import copy
import struct
from .observations import observation, validate_clock

_UNKNOWN = (1 << 64) - 1
_SEMANTICS = {
    1: 'issue',
    2: 'wait_bracket',
    3: 'control_checkpoint',
    4: 'operation_checkpoint'
}
_MANIFEST_SEMANTICS = {
    'signal_issue_source_control': 1,
    'existing_readiness_wait_source_control': 2,
    'loop_header_occurrence': 3,
    'source_operation_checkpoint': 4
}
_CALLEE_SEMANTICS = {
    'llvm.hivm.SET.FLAG.IMM': 1,
    'llvm.hivm.SET.CROSS.CORE': 1,
    'llvm.hivm.WAIT.FLAG.IMM': 2,
    'llvm.hivm.WAIT.FLAG.DEV.REG': 2
}


def _validate_site_semantic(manifest, code):
    if manifest is None:
        return False
    declared = _MANIFEST_SEMANTICS.get(manifest.get('semantics'))
    callee = manifest.get('callee')
    native = _CALLEE_SEMANTICS.get(callee)
    if declared is not None and declared != code or native is not None and native != code:
        raise ValueError(
            'dynamic64 event semantic contradicts authoritative compiler site')
    if declared == 3 and callee is not None:
        raise ValueError(
            'dynamic64 checkpoint compiler site has a native callee')
    return declared is not None and (native is not None or declared in (3, 4))


def decode_dynamic64(data,
                     *,
                     capacity,
                     actor_slots=3,
                     capture_id,
                     invocation_id=None,
                     association_evidence=None,
                     clock=None,
                     site_manifest=None,
                     expected_program=None,
                     require_actor_binding=False):
    """Decode actor_header4_record8_v1 with independent cursor/overflow counts.

    Zero headers denote no recorded selected event; actor execution is unknown.
    ``occurrence`` is actor-log order,
    not a source loop index. Clock conversion requires separately supplied
    evidence; independent replay clocks are never joined here.
    """
    if type(capacity) is not int or capacity < 1 or type(
            actor_slots) is not int or actor_slots < 1:
        raise ValueError('capacity and actor_slots must be positive integers')
    if expected_program is not None and (
            type(expected_program) is not int
            or not 0 <= expected_program <= _UNKNOWN):
        raise ValueError(
            'expected_program must be an unsigned64 integer or None')
    if not isinstance(capture_id, str) or not capture_id:
        raise ValueError('capture_id must be nonempty')
    if isinstance(data, (bytes, bytearray, memoryview)):
        if len(data) % 8:
            raise ValueError(
                'dynamic64 byte length must be divisible by eight')
        words = list(struct.unpack('<' + 'Q' * (len(data) // 8), data))
    else:
        words = list(data)
        if any(
                type(word) is not int or word < -(1 << 63) or word > _UNKNOWN
                for word in words):
            raise ValueError(
                'dynamic64 words must fit a signed/unsigned64 carrier')
        words = [word & _UNKNOWN for word in words]
    expected = actor_slots * (4 + capacity * 8)
    if len(words) < expected:
        raise ValueError('truncated dynamic64 allocation')
    if any(
            type(word) is not int or word < 0 or word > _UNKNOWN
            for word in words[:expected]):
        raise ValueError('dynamic64 words must be unsigned64')
    native_clock = validate_clock(
        clock or {
            'domain': 'ascend.SYS_CNT',
            'scope': 'actor_local',
            'alignment': 'instance_local',
            'tick_ns': None,
            'wrap_bits': 64
        })
    sites = {}
    ambiguous_sites = set()
    for entry in (site_manifest or []):
        actor = entry.get('actor_slot')
        if type(actor) is not int or actor < 0:
            continue
        key = (actor, entry['site_id'])
        if key in sites:
            ambiguous_sites.add(key)
        else:
            sites[key] = entry
    events, actors = [], []
    for actor in range(actor_slots):
        base = actor * (4 + capacity * 8)
        version, cursor, attempted, dropped = words[base:base + 4]
        if version == 0:
            if cursor or attempted or dropped:
                raise ValueError(
                    'uninitialized actor header has nonzero statistics')
            actors.append({
                'actor_slot': actor,
                'state': 'no_records',
                'execution_status': 'unknown',
                'binding_status': 'unknown_no_records',
                'committed': 0,
                'attempted': 0,
                'dropped': 0
            })
            continue
        if version != 1:
            raise ValueError('unsupported dynamic64 version')
        if cursor > capacity or attempted != cursor + dropped:
            raise ValueError(
                'inconsistent dynamic64 cursor/overflow statistics')
        actors.append({
            'actor_slot': actor,
            'state': 'truncated' if dropped else 'complete',
            'committed': cursor,
            'attempted': attempted,
            'dropped': dropped
        })
        prior = -1
        for index in range(cursor):
            record = words[base + 4 + index * 8:base + 4 + (index + 1) * 8]
            descriptor, occurrence, start, end, program, recorded_actor, buffer_slot, iteration = record
            site, code = descriptor & 0xffffffff, descriptor >> 32
            if code not in _SEMANTICS:
                raise ValueError('unknown dynamic64 event semantic')
            if recorded_actor != actor or occurrence <= prior or occurrence >= attempted:
                raise ValueError(
                    'dynamic64 actor/occurrence identity mismatch')
            if code in (3, 4) and start != end:
                raise ValueError(
                    'checkpoint point record has nonzero interval')
            if expected_program is not None and program != expected_program:
                raise ValueError(
                    'dynamic64 program contradicts compiled program selection')
            prior = occurrence
            manifest = None if (actor, site) in ambiguous_sites else sites.get(
                (actor, site))
            site_semantic_verified = _validate_site_semantic(manifest, code)
            compiler_actor = (manifest or {}).get('compiler_actor')
            verified_actor = False
            if compiler_actor:
                binding = compiler_actor.get('runtime_actor_binding') or {}
                proof = compiler_actor.get('binding_proof') or {}
                verified_actor = (
                    actor in binding.get('admissible_slots', [])
                    and binding.get('segment_count') == actor_slots
                    and binding.get('segment_words') == 4 + capacity * 8
                    and proof.get('status')
                    == 'verified_compiler_emission_manifest'
                    and compiler_actor.get('module_sha256')
                    == binding.get('module_sha256')
                    and compiler_actor.get('compile_id')
                    == binding.get('compile_id') and
                    compiler_actor.get('function') == binding.get('function')
                    and compiler_actor.get('id') ==
                    f"late_llvm:{binding.get('module_sha256')}:{binding.get('function')}"
                )
                if not verified_actor:
                    raise ValueError(
                        'raw actor slot contradicts compiler runtime binding')
            if require_actor_binding and (not verified_actor
                                          or not site_semantic_verified):
                raise ValueError(
                    'automatic raw record lacks unambiguous compiler actor binding'
                )
            if verified_actor:
                manifest = copy.deepcopy(manifest)
                proof = manifest['compiler_actor']['binding_proof']
                proof['observed_actor_slot'] = actor
                proof[
                    'runtime_slot_status'] = 'verified_against_raw_record_and_segment'
                actors[-1]['binding_status'] = 'verified_by_committed_records'
                identities = actors[-1].setdefault('compiler_actors', [])
                identity = manifest['compiler_actor']['id']
                if identity not in identities:
                    identities.append(identity)
            event = {
                'program_selection_status':
                'consistent_with_expected_program'
                if expected_program is not None else 'unverified_legacy',
                'expected_program':
                expected_program,
                'id':
                f'{capture_id}:actor{actor}:record{index}',
                'capture_id':
                capture_id,
                'invocation_id':
                invocation_id,
                'source':
                'ascend_llvm_dynamic64',
                'semantic':
                _SEMANTICS[code],
                'event_kind':
                'loop_header_occurrence'
                if code == 3 else 'source_operation_occurrence'
                if code == 4 else 'native_primitive_bracket',
                'program':
                program,
                'actor_slot':
                actor,
                'site':
                site,
                'occurrence':
                occurrence,
                'start_tick':
                start,
                'end_tick':
                end,
                'buffer_slot':
                None if buffer_slot == _UNKNOWN else buffer_slot,
                'iteration':
                None if iteration == _UNKNOWN else iteration,
                'clock':
                native_clock,
                'association_status':
                'verified'
                if invocation_id and association_evidence else 'unassociated',
                'association_evidence':
                association_evidence,
                'original_record':
                record,
                'compiler_actor_status':
                'verified_against_raw_record_and_segment'
                if verified_actor else 'unverified_legacy',
                'compiler_site':
                manifest,
                'source_mapping_status':
                'ambiguous' if
                (actor,
                 site) in ambiguous_sites else 'partial' if manifest is None
                or not site_semantic_verified else 'compiler_site_identified',
                'limits': [
                    'An issue/wait bracket measures source control; it is not engine busy.',
                    'Actor occurrence order does not identify a source loop induction variable.'
                ]
            }
            events.append(observation(event))
    return {
        'schema_version': 1,
        'backend': 'ascend',
        'layout': 'actor_header4_record8_v1',
        'capture_id': capture_id,
        'invocation_id': invocation_id,
        'actors': actors,
        'observations': events,
        'dropped': sum(actor['dropped'] for actor in actors),
        'program_selection': {
            'expected_program':
            expected_program,
            'status':
            'checked_against_expected_program'
            if expected_program is not None else 'unverified_legacy'
        }
    }
