"""Independent reader for the frozen r2 public Ascend binding contract.

No product imports or execution. Original and adapted LLVM are opaque captured
bytes: their hashes bind the emission manifest, not an invented LLVM parser.
"""
import base64
from collections import Counter
import hashlib
import json
import struct

from check_common_report import integer, require
from c1_public_plan import validate_control_entry

SEMANTIC_KIND = {'issue': 1, 'wait_bracket': 2, 'control_checkpoint': 3,
                 'operation_checkpoint': 4}


def text_digest(value):
    require(isinstance(value, str), 'captured compiler text missing')
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def binding_contract(binding, function, kind, module, compile_id):
    require(kind in ['AIC', 'AIV'], 'unknown compiler actor kind')
    expected = dict(schema_version=1, function=function, actor_kind=kind,
                    module_sha256=module, compile_id=compile_id,
                    layout='actor_header4_record8_v1', segment_count=3,
                    record_actor_word=5,
                    admissible_slots=[0] if kind == 'AIC' else [1, 2],
                    expression={'kind': 'constant_i64', 'value': 0} if kind == 'AIC' else
                    {'kind': 'add_i64', 'call': 'llvm.hivm.GET.SUBBLOCKID', 'constant': 1},
                    value_use='same_emitted_i64_for_segment_offset_and_record_word5',
                    basis='actual_emitted_logger_actor_value')
    require(isinstance(binding, dict) and all(binding.get(k) == v for k, v in expected.items()),
            'compiler runtime actor binding contract mismatch')
    words = binding.get('segment_words')
    require(integer(words) and words > 4 and (words - 4) % 8 == 0,
            'invalid compiler actor segment capacity')
    return (words - 4) // 8


def verify_ascend_plans(document, binary_ids):
    require(document.get('schema_version') == 1, 'plan envelope major version')
    require(isinstance(document.get('capture_evidence'), list), 'missing plan capture evidence')
    entries = document.get('plans')
    require(isinstance(entries, list) and entries, 'no automatic inventory/plan')
    selected_by_binary = {binary: set() for binary in binary_ids}
    summaries = []
    for entry in entries:
        if entry.get('binary_id') not in binary_ids:
            continue
        plan = entry.get('plan', {})
        kind = entry.get('plan_kind')
        require(kind in ['operation', 'control'], 'missing/unknown typed Ascend plan kind')
        inventory = plan.get('inventory')
        require(isinstance(inventory, list), 'missing actual compiler candidate inventory')
        if kind == 'control':
            selected = validate_control_entry(entry)
        else:
            require(inventory, 'missing actual compiler operation candidate inventory')
            require(isinstance(plan.get('policy'), str) and plan['policy'], 'missing automatic policy')
            require(integer(plan.get('max_sites')) and plan['max_sites'] > 0, 'missing bounded site budget')
            require(plan.get('budget_scope') == 'source_operation_candidates_only'
                    and plan.get('control_sites_included') is False, 'operation budget scope mismatch')
            require(all(isinstance(item.get('selected'), bool) for item in inventory), 'inventory selection flags missing')
            selected = [item for item in inventory if item['selected']]
            require(selected and len(selected) <= plan['max_sites'], 'operation site budget exceeded/empty')
            count = plan.get('candidate_count')
            require(integer(count) and len(selected) <= count <= len(inventory), 'actual candidate inventory/count mismatch')
            require(plan.get('selected_count') == len(selected), 'Ascend selected count mismatch')
        ids = []
        for item in inventory:
            site = item.get('site_id')
            require(integer(site) and site >= 0 and site not in ids, 'duplicate/invalid compiler site ID')
            ids.append(site)
            require(isinstance(item.get('selection_reason'), str) and item['selection_reason'], 'selection/exclusion reason missing')
            require(item.get('public_semantic') in SEMANTIC_KIND, 'unknown public semantic')
            require((item['public_semantic'] == 'operation_checkpoint') == (kind == 'operation'), 'semantic in wrong plan class')
            require(isinstance(item.get('operation'), str) and item['operation'], 'original compiler operation missing')
            require(isinstance(item.get('source_file'), str) and item['source_file']
                    and integer(item.get('line')) and item['line'] > 0, 'compiler source provenance missing')
            if kind == 'control' and not item['selected']:
                require(item['selection_reason'] == 'semantic_not_requested', 'unrequested control exclusion unexplained')
        require(isinstance(entry.get('compile_id'), str) and entry['compile_id'], 'plan compile identity missing')
        require(isinstance(entry.get('module_sha256'), str) and len(entry['module_sha256']) == 64, 'plan module identity missing')
        declarations = entry.get('compiler_actors')
        require(isinstance(declarations, list) and declarations, 'compiler actor declarations missing')
        actor_ids = set()
        for declaration in declarations:
            function = declaration.get('function')
            require(isinstance(function, str) and function, 'compiler function missing')
            identity = f"late_llvm:{entry['module_sha256']}:{function}"
            require(declaration.get('identity') == identity and identity not in actor_ids, 'compiler actor identity mismatch/duplicate')
            actor_ids.add(identity)
            capacity = binding_contract(declaration.get('runtime_actor_binding'), function,
                                        declaration.get('actor_kind'), entry['module_sha256'], entry['compile_id'])
            if kind == 'control':
                require(capacity == plan['record_capacity_per_actor'], 'control dynamic capacity differs from binding')
        selected_by_binary[entry['binary_id']].update(item['site_id'] for item in selected)
        summaries.append(dict(binary_id=entry['binary_id'], module_sha256=entry['module_sha256'],
                              compile_id=entry['compile_id'], plan_kind=kind,
                              candidate_count=len(inventory), selected_count=len(selected)))
    require(all(selected_by_binary.values()), 'binary has no actual selected-site plan')
    return selected_by_binary, summaries


def verify_actor_record(row, observation, capture, entries, binary):
    """Require one complete applicable entry; never union identities or sites."""
    actor = row.get('compiler_actor')
    require(isinstance(actor, dict), 'normalized compiler actor missing')
    compiler_site = observation.get('compiler_site', {})
    require(compiler_site.get('compiler_actor') == actor, 'original/normalized compiler actor differ')
    require(observation.get('compiler_actor_status') == 'verified_against_raw_record_and_segment', 'original actor binding unverified')
    for key in ['capture_id', 'invocation_id', 'site', 'semantic', 'program', 'occurrence', 'start_tick', 'end_tick']:
        require(row.get(key) == observation.get(key), f'original/normalized record differ: {key}')
    require(observation.get('association_evidence', {}).get('binary_id') == row['binary_id'], 'original binary association mismatch')
    slot = row.get('actor')
    require(integer(slot) and slot == observation.get('actor_slot') == compiler_site.get('actor_slot'), 'measured/original actor slot mismatch')
    function, module, compile_id = [actor.get(key) for key in ['function', 'module_sha256', 'compile_id']]
    require(actor.get('id') == f'late_llvm:{module}:{function}', 'record compiler actor ID mismatch')
    binding = actor.get('runtime_actor_binding')
    binding_contract(binding, function, actor.get('kind'), module, compile_id)
    require(slot in binding['admissible_slots'], 'raw slot inadmissible for actual compiler actor')
    applicable = []
    for entry in entries:
        if not (entry.get('binary_id') == row['binary_id'] and entry.get('module_sha256') == module
                and entry.get('compile_id') == compile_id):
            continue
        if entry.get('capture_id') is not None and entry['capture_id'] != row['capture_id']:
            continue
        declarations = [d for d in entry.get('compiler_actors', []) if d.get('identity') == actor['id']
                        and d.get('function') == function and d.get('actor_kind') == actor['kind']
                        and d.get('runtime_actor_binding') == binding]
        matches = [i for i in entry['plan']['inventory'] if i.get('selected') is True
                   and i.get('site_id') == row['site'] and i.get('public_semantic') == row['semantic']]
        if len(declarations) == 1 and len(matches) == 1:
            applicable.append((entry, matches[0]))
    require(len(applicable) == 1, 'record lacks unique selected inventory in exact binary/module/compile/function/semantic')
    entry, item = applicable[0]
    for key in ['site_id', 'public_semantic', 'operation', 'source_file', 'line']:
        require(compiler_site.get(key) == item.get(key), f'raw compiler-site inventory mismatch: {key}')
    require(row.get('operation') == item['operation'], 'normalized operation differs from selected inventory')
    handoff = binary.get('compiler_metadata', {}).get('flagprism_ascend_handoff', {})
    require(handoff.get('compile_id') == compile_id, 'binary handoff compile mismatch')
    artifacts = [a for a in handoff.get('artifacts', []) if a.get('sha256') == module]
    require(len(artifacts) == 1, 'binary lacks unique exact compiler module')
    artifact = artifacts[0]
    metadata = artifact.get('metadata')
    require(isinstance(metadata, dict) and json.loads(artifact['manifest_text']) == metadata, 'manifest text/metadata mismatch')
    require(text_digest(artifact['manifest_text']) == artifact.get('manifest_sha256'), 'compiler manifest digest mismatch')
    require(text_digest(artifact.get('llir')) == module, 'original compiler module digest mismatch')
    adapted = artifact.get('adapted', {})
    require(text_digest(adapted.get('llir')) == adapted.get('sha256'), 'adapted compiler module digest mismatch')
    require(metadata.get('module_sha256') == module and metadata.get('compile_id') == compile_id, 'compiler manifest identity mismatch')
    require(metadata.get('runtime_actor_binding') == binding, 'manifest emission binding mismatch')
    require(any(a.get('function') == function and a.get('actor_kind') == actor['kind'] for a in metadata.get('actors', [])), 'function absent from exact module manifest')
    require(metadata.get(entry['plan_kind'] + '_plan') == entry['plan'], 'selected plan differs from exact module manifest')
    require(any(s.get('site_id') == row['site'] and s.get('public_semantic') == row['semantic']
                and s.get('operation') == item['operation'] for s in metadata.get('dynamic_sites', [])), 'record absent from module dynamic sites')
    proof = actor.get('binding_proof', {})
    expected = dict(status='verified_compiler_emission_manifest',
                    manifest_sha256=artifact['manifest_sha256'], original_module_sha256=module,
                    adapted_module_sha256=adapted['sha256'],
                    selection_membership='selected_dynamic_site_in_exact_module_plan',
                    observed_actor_slot=slot, runtime_slot_status='verified_against_raw_record_and_segment')
    require(all(proof.get(k) == v for k, v in expected.items()), 'compiler actor binding proof mismatch')
    raw = observation.get('original_record')
    require(isinstance(raw, list) and len(raw) == 8 and all(integer(w) and 0 <= w < 2**64 for w in raw), 'raw uint64 record missing')
    require(raw[0] & 0xffffffff == row['site'] and raw[0] >> 32 == SEMANTIC_KIND.get(row['semantic']), 'raw descriptor site/semantic mismatch')
    require(raw[1] == row['occurrence'] and raw[2] == row['start_tick'] and raw[3] == row['end_tick']
            and raw[4] == row['program'] and raw[5] == slot, 'raw record measured identity/ticks mismatch')
    actor_rows = [a for a in capture.get('actors', []) if a.get('actor_slot') == slot]
    require(len(actor_rows) == 1 and actor_rows[0].get('binding_status') == 'verified_by_committed_records'
            and actor['id'] in actor_rows[0].get('compiler_actors', []), 'capture slot compiler binding missing')
    return binding


def verify_ascend_records(records, original, document, binary_map):
    observations = original['observations']
    ids = [o.get('id') for o in observations]
    require(len(ids) == len(set(ids)), 'duplicate original observation ID')
    by_id = {o['id']: o for o in observations}
    captures = {c['capture_id']: c for c in original['captures']}
    bindings = {}
    for row in records:
        require(row['id'] in by_id and row['capture_id'] in captures, 'original observation/capture absent')
        binding = verify_actor_record(row, by_id[row['id']], captures[row['capture_id']],
                                      document['plans'], binary_map[row['binary_id']])
        key = row['capture_id']
        if key in bindings:
            require(bindings[key]['segment_words'] == binding['segment_words'], 'capture has conflicting segment sizes')
        bindings[key] = binding
    for cid, binding in bindings.items():
        capture = captures[cid]
        require({r['id'] for r in records if r['capture_id'] == cid}
                == {o['id'] for o in observations if o.get('capture_id') == cid},
                'normalized view omits or invents original retained internal records')
        require(capture.get('record_layout') == 'ascend_actor_dynamic_v1'
                and capture.get('raw_encoding') == 'base64_ascend_actor_dynamic_v1', 'raw actor layout missing')
        raw = base64.b64decode(capture['raw_base64'], validate=True)
        require(hashlib.sha256(raw).hexdigest() == capture.get('raw_sha256'), 'raw allocation digest mismatch')
        segment_words = binding['segment_words']
        require(len(raw) == 3 * segment_words * 8, 'raw allocation segment size mismatch')
        words = struct.unpack('<' + 'Q' * (len(raw) // 8), raw)
        actor_rows = capture.get('actors', [])
        require(sorted(a.get('actor_slot') for a in actor_rows) == [0, 1, 2], 'capture actor segments missing/duplicate')
        for slot in range(3):
            segment = words[slot * segment_words:(slot + 1) * segment_words]
            actor_row = next(a for a in actor_rows if a['actor_slot'] == slot)
            committed = actor_row['committed']
            require(segment[1:4] == (actor_row['attempted'], committed, actor_row['dropped']), 'raw actor header accounting mismatch')
            require(committed <= (segment_words - 4) // 8, 'raw committed count exceeds capacity')
            retained = [tuple(segment[4 + n * 8:12 + n * 8]) for n in range(committed)]
            require(all(r[5] == slot for r in retained), 'raw actor word differs from actual segment')
            projected = [tuple(o['original_record']) for o in observations if o.get('capture_id') == cid and o.get('actor_slot') == slot]
            require(Counter(retained) == Counter(projected), 'original observations differ from committed raw allocation')
            if committed:
                observed_ids = {o['compiler_site']['compiler_actor']['id'] for o in observations
                                if o.get('capture_id') == cid and o.get('actor_slot') == slot}
                require(set(actor_row.get('compiler_actors', [])) == observed_ids,
                        'capture actor declarations differ from actual committed records')
            if not committed:
                require(actor_row.get('binding_status') == 'unknown_no_records'
                        and actor_row.get('execution_status') == 'unknown', 'empty slot falsely proves execution')
