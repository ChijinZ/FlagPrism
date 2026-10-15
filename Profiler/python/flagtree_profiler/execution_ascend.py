"""Static Ascend actor/CFG evidence from actual compiler LLVM artifacts.

Source IR and requested pipeline options do not prove final actor assignment.
Final actor types require compiler artifact provenance or surviving attributes;
source IDs and workspace roles require explicit compiler metadata.
"""
from __future__ import annotations
import hashlib
import json
import posixpath
import re
from collections.abc import Mapping

_SSA = r'%[\w.$]+'
_FUNCTION = re.compile(r'^define\s+.*?@([\w.$]+)\((.*)\).*\{\s*$', re.M)
_CALL = re.compile(r'\bcall\s+[^@]*@([\w.$]+)\((.*)\)')
_BINARY = {'add': '+', 'sub': '-', 'mul': '*', 'sdiv': '//', 'udiv': '//', 'srem': '%', 'urem': '%', 'and': '&', 'or': '|', 'shl': '<<', 'lshr': '>>'}
_SEMANTICS = {'llvm.hivm.SET.CROSS.CORE': 'readiness_signal_issue', 'llvm.hivm.WAIT.FLAG.DEV.REG': 'readiness_wait', 'llvm.hivm.SET.FLAG.IMM': 'pipeline_event_signal_issue', 'llvm.hivm.WAIT.FLAG.IMM': 'pipeline_event_wait', 'llvm.hivm.BARRIER': 'existing_pipeline_barrier'}


def _components(graph):
    """Return cyclic strongly connected CFG components, including self loops."""
    index, low, stack, active, result = {}, {}, [], set(), []
    def visit(node):
        index[node] = low[node] = len(index)
        stack.append(node)
        active.add(node)
        for child in graph.get(node, []):
            if child not in index:
                visit(child)
                low[node] = min(low[node], low[child])
            elif child in active:
                low[node] = min(low[node], index[child])
        if low[node] == index[node]:
            component = []
            while True:
                value = stack.pop()
                active.remove(value)
                component.append(value)
                if value == node:
                    break
            if len(component) > 1 or node in graph.get(node, []):
                result.append(sorted(component))
    for node in graph:
        if node not in index:
            visit(node)
    return result


def build_execution_mapping(asm: Mapping, compiler_metadata: Mapping, *, binary_id=None, source_operations=None):
    """Decode final LLVM into actor, pointer, event and loop evidence.

    ``artifact_actor_kinds`` maps artifact keys to AIC/AIV using compiler output
    provenance. ``argument_roles`` optionally maps artifact keys and formal
    argument positions to roles (e.g. workspace). Missing roles stay unknown.
    This decoder does not infer source IDs from symbols or source locations,
    decode undocumented cross-core flag encodings, or infer dynamic iterations.
    """
    artifacts = {key: value for key, value in asm.items() if isinstance(value, str)}
    evidence = {key: {'sha256': hashlib.sha256(value.encode()).hexdigest(), 'bytes': len(value.encode())} for key, value in artifacts.items()}
    actor_kinds = compiler_metadata.get('artifact_actor_kinds', {})
    argument_roles = compiler_metadata.get('argument_roles', {})
    source_ids = set(source_operations or ())
    actors, sites, loops, pointers, associations = [], [], [], [], []
    for artifact, text in artifacts.items():
        if not _FUNCTION.search(text):
            continue
        annotations = set(re.findall(r'!\{ptr @([\w.$]+), !"kernel", i32 1\}', text))
        metadata_ids = dict(re.findall(r'!(\d+)\s*=\s*!\{!"([^"\n]+)"\}', text))
        for match in _FUNCTION.finditer(text):
            function = match[1]
            end = text.find('\n}', match.end())
            if end == -1:
                continue
            header = text[match.start():match.end()]
            if function not in annotations and not re.search(r'\b(?:dso_local|spir_kernel)\b', header):
                continue
            body = text[match.end():end]
            offset = text.count('\n', 0, match.end())
            actor_id = f'{artifact}:{evidence[artifact]["sha256"]}:{function}'
            kind = actor_kinds.get(artifact)
            basis = 'compiler_artifact_provenance' if kind in {'AIC', 'AIV'} else None
            type_attribute = re.search(r'"(?:hivm\.)?(?:func_)?core_type"\s*=\s*"(AIC|AIV)"', header)
            if type_attribute:
                kind, basis = type_attribute[1], 'surviving_compiler_core_attribute'
            if kind not in {'AIC', 'AIV'}:
                kind = None
            actors.append({'id': actor_id, 'kind': kind, 'kind_basis': basis, 'artifact': artifact, 'function': function, 'program': 'GET.BLOCK.IDX()', 'subblock': 'GET.SUBBLOCKID()' if '@llvm.hivm.GET.SUBBLOCKID()' in body else None, 'mapping_status': 'symbolic' if kind else 'partial'})
            expressions, graph, block, block_sites, phis = {}, {}, 'entry', {}, []
            for position, argument in enumerate(match[2].split(',')):
                pointer = re.search(r'ptr\s+addrspace\((\d+)\)\s+(' + _SSA + ')', argument)
                if pointer:
                    role = argument_roles.get(artifact, {}).get(str(position), argument_roles.get(artifact, {}).get(position))
                    pointers.append({'id': actor_id + f':arg{position}', 'actor_id': actor_id, 'argument_position': position, 'ssa': pointer[2], 'address_space': int(pointer[1]), 'role': role, 'role_basis': 'compiler_argument_metadata' if role else 'unknown', 'measured': False})
            for relative_line, line in enumerate(body.splitlines(), 1):
                line_number = offset + relative_line
                label = re.match(r'^([\w.$]+):', line)
                if label:
                    block = label[1]
                graph.setdefault(block, [])
                if re.search(r'\bbr\b', line):
                    graph[block].extend(re.findall(r'label\s+%([\w.$]+)', line))
                definition = re.match(r'\s*(' + _SSA + r')\s*=\s*(.*)', line)
                if definition:
                    result, instruction = definition.groups()
                    arithmetic = re.match(r'(\w+)\s+(?:nuw\s+|nsw\s+)*i\d+\s+([^,]+),\s*([^,;]+)', instruction)
                    if arithmetic and arithmetic[1] in _BINARY:
                        left, right = [expressions.get(v.strip(), v.strip()) for v in arithmetic.groups()[1:]]
                        expression = f'({left} {_BINARY[arithmetic[1]]} {right})'
                        expressions[result] = expression if len(expression) < 2048 else result
                    elif instruction.startswith('phi '):
                        phis.append({'ssa': result, 'block': block, 'expression': instruction, 'line': line_number})
                    elif re.match(r'(?:trunc|sext|zext)\s+', instruction):
                        operand = re.search(_SSA, instruction)
                        if operand:
                            expressions[result] = expressions.get(operand[0], operand[0])
                call = _CALL.search(line)
                if not call:
                    continue
                callee = call[1]
                if definition and callee in {'llvm.hivm.GET.BLOCK.IDX', 'llvm.hivm.GET.SUBBLOCKID'}:
                    expressions[definition[1]] = 'program.block' if callee.endswith('IDX') else 'actor.subblock'
                operands = re.findall(r'(?:i\d+\s+)(-?\d+|' + _SSA + ')', call[2])
                values = [expressions.get(value, value) for value in operands]
                if callee not in _SEMANTICS and not any('program.' in value or 'actor.' in value for value in values):
                    continue
                site_id = actor_id + f':line{line_number}'
                source_ref = re.search(r'!flagprism\.source_op_id\s+!(\d+)', line)
                source_id = metadata_ids.get(source_ref[1]) if source_ref else None
                sites.append({'id': site_id, 'actor_id': actor_id, 'block': block, 'line': line_number, 'callee': callee, 'semantics': _SEMANTICS.get(callee, 'static_issue_site'), 'operands': operands, 'operand_expressions': values, 'evidence': line.strip(), 'source_op_id': source_id, 'dynamic_observation': False})
                block_sites.setdefault(block, []).append(site_id)
            for number, blocks in enumerate(_components(graph)):
                loops.append({'id': actor_id + f':cycle{number}', 'actor_id': actor_id, 'blocks': blocks, 'induction_candidates': [phi for phi in phis if phi['block'] in blocks], 'sites': [site for label in blocks for site in block_sites.get(label, [])], 'dynamic_iteration_count': None})
    # The real LLVM pass manifest is authoritative when the driver handoff is
    # available. It also works when CompiledKernel.asm omits temporary LLVM.
    handoff = compiler_metadata.get('flagprism_ascend_handoff') or {}
    from .ascend_hivm import build_static_readiness, validate_compiler_provenance
    provenance = validate_compiler_provenance(
        handoff.get('sdk_ir_capture'),
        handoff.get('artifacts', []),
        source_snapshot=handoff.get('source_snapshot'),
        compile_id=handoff.get('compile_id'),
        phase=handoff.get('phase'),
        returncode=handoff.get('returncode'))
    snapshot = handoff.get('source_snapshot') or {}
    tracked = list(source_operations.values()) if isinstance(
        source_operations, Mapping) else None
    table_hash = hashlib.sha256(
        json.dumps(tracked, sort_keys=True, separators=(
            ',', ':')).encode()).hexdigest() if tracked is not None else None
    snapshot_verified = (provenance['state'] == 'verified_source_binding'
                         and table_hash is not None
                         and snapshot.get('tracked_ops_sha256') == table_hash)
    provenance[
        'tracked_table_state'] = 'verified' if snapshot_verified else 'unverified_or_missing'
    native_items = [(index, item.get('metadata'))
                    for index, item in enumerate(handoff.get('artifacts', []))
                    if isinstance(item.get('metadata'), dict)]
    native_manifests = [manifest for _, manifest in native_items]
    if native_manifests:
        actors, sites, loops, pointers, associations = [], [], [], [], []
        for artifact_index, manifest in native_items:
            artifact_verified = artifact_index in provenance[
                'verified_artifact_indices']
            source_verified = snapshot_verified and artifact_verified
            artifact_state = 'verified_same_compile_artifact' if artifact_verified else 'unverified_manifest_inventory'
            module_id = manifest.get('module_sha256')
            for raw_actor in manifest.get('actors', []):
                actor_id = f'late_llvm:{module_id}:{raw_actor["function"]}'
                actors.append({
                    'id':
                    actor_id,
                    'kind':
                    raw_actor.get('actor_kind') or None,
                    'kind_basis':
                    'actual_sdk_target_argument'
                    if artifact_verified else 'unverified_manifest_claim',
                    'function':
                    raw_actor['function'],
                    'artifact':
                    module_id,
                    'mapping_status':
                    'symbolic',
                    'native_artifact_provenance':
                    artifact_state,
                    'compiler_manifest':
                    raw_actor
                })
                roles = {role['final_formal_index']: role for role in raw_actor.get('argument_roles', [])}
                for argument in raw_actor.get('arguments', []):
                    if argument.get('address_space') != 1:
                        continue
                    role = roles.get(argument['position'], {})
                    pointers.append({'id': actor_id+f':arg{argument["position"]}', 'actor_id': actor_id, 'argument_position': argument['position'], 'ssa': argument['ssa'], 'address_space': 1, 'role': role.get('role'), 'role_basis': role.get('basis', 'unknown'), 'source_argument_index': role.get('source_argument_index'), 'measured': False})
                for raw_site in raw_actor.get('sites', []):
                    site_id = actor_id+f':site{raw_site["id"]}'
                    source_id = raw_site.get('source_op_id')
                    site = {
                        'id':
                        site_id,
                        'actor_id':
                        actor_id,
                        'callee':
                        raw_site['callee'],
                        'semantics':
                        _SEMANTICS.get(raw_site['callee'],
                                       'static_issue_site'),
                        'operand_expressions':
                        raw_site['operands'],
                        'source_op_id':
                        source_id,
                        'compiler_evidence':
                        raw_site,
                        'native_artifact_provenance':
                        artifact_state,
                        'dynamic_observation':
                        False
                    }
                    sites.append(site)
                    if source_verified and source_id and (
                            not source_ids or source_id in source_ids):
                        associations.append({'source_op_id': source_id, 'lowered_site_id': site_id, 'basis': 'surviving_compiler_metadata'})
                for index, loop in enumerate(raw_actor.get('loops', [])):
                    loops.append({'id': actor_id+f':loop{index}', 'actor_id': actor_id, 'blocks': loop['blocks'], 'dynamic_iteration_count': None, 'compiler_evidence': loop})
                if len(manifest.get('actors', [])) == 1:
                    for raw_site in manifest.get('dynamic_sites', []):
                        callee = raw_site.get('callee')
                        semantic = 'control_checkpoint' if raw_site.get('semantics') == 'loop_header_occurrence' else 'wait_bracket' if callee and '.WAIT.' in callee else 'issue'
                        sites.append({
                            'id':
                            actor_id + f':dynamic{raw_site["site_id"]}',
                            'actor_id':
                            actor_id,
                            'dynamic_site_id':
                            raw_site['site_id'],
                            'callee':
                            callee,
                            'semantics':
                            semantic,
                            'operand_expressions': [],
                            'source_op_id':
                            raw_site.get('source_op_id'),
                            'compiler_evidence':
                            raw_site,
                            'native_artifact_provenance':
                            artifact_state,
                            'dynamic_observation':
                            True
                        })
                        if source_verified and raw_site.get(
                                'source_op_id') and (
                                    not source_ids
                                    or raw_site['source_op_id'] in source_ids):
                            associations.append({'source_op_id': raw_site['source_op_id'],
                                                 'lowered_site_id': sites[-1]['id'],
                                                 'basis': 'surviving_compiler_metadata'})
    # Match full debug origin only against the tracked table from this exact
    # retained compiler snapshot. Debug origin never grants exclusive cost.
    origin_associations = []
    if isinstance(source_operations, Mapping) and native_manifests:
        location_pattern = re.compile(r'"((?:\\.|[^"\\])+)":(\d+):(\d+)')
        def entry_locations(entry):
            return [(posixpath.normpath(file), int(line), int(column)) for file, line, column in location_pattern.findall(entry.get('sourceLoc', ''))]
        for site in sites:
            raw = site.get('compiler_evidence') or {}
            file = raw.get('debug_file')
            frames = []
            if file:
                frames.append((posixpath.normpath(posixpath.join(raw.get('debug_directory', ''), file)), raw.get('debug_line'), raw.get('debug_column')))
                frames += [(posixpath.normpath(posixpath.join(frame.get('directory', ''), frame['file'])), frame['line'], frame['column']) for frame in raw.get('inline_chain', [])]
            candidates = [
                str(identity) for identity, entry in source_operations.items()
                if frames and entry_locations(entry) == frames
            ] if snapshot_verified and site.get(
                'native_artifact_provenance'
            ) == 'verified_same_compile_artifact' else []
            site['debug_origin_status'] = 'verified_origin' if len(candidates) == 1 else 'ambiguous' if candidates else 'unassociated'
            site['debug_origin_candidates'] = candidates
            if len(candidates) == 1:
                origin_associations.append({'source_op_id': candidates[0], 'lowered_site_id': site['id'], 'basis': 'unique_full_debug_location_in_verified_compiler_snapshot', 'status': 'verified_origin', 'cost_ownership': 'not_established', 'source_ir_sha256': snapshot['ir_sha256']})
        associations.extend(origin_associations)
    static_readiness = build_static_readiness(
        handoff.get('sdk_ir_capture'),
        handoff.get('artifacts', []),
        source_snapshot=handoff.get('source_snapshot'),
        compile_id=handoff.get('compile_id'),
        phase=handoff.get('phase'),
        returncode=handoff.get('returncode'))
    for channel in static_readiness['channels']:
        producers = [
            actor for actor in actors
            if actor['function'] == channel['producer_function']
            and actor['kind'] == channel['producer_actor_kind']
        ]
        consumers = [
            actor for actor in actors
            if actor['function'] == channel['consumer_function']
            and actor['kind'] == channel['consumer_actor_kind']
        ]
        if len(producers) == 1 and len(consumers) == 1:
            channel['producer_actor_id'] = producers[0]['id']
            channel['consumer_actor_id'] = consumers[0]['id']
    dependencies = []
    for site in sites:
        if site['semantics'] in {'readiness_signal_issue', 'readiness_wait'}:
            dependencies.append({'site_id': site['id'], 'actor_id': site['actor_id'], 'semantics': site['semantics'], 'native_operands': site['operand_expressions'], 'peer_site_id': None, 'state': 'unresolved_native_event_encoding'})
    return {
        'schema_version':
        1,
        'backend':
        'ascend',
        'binary_id':
        binary_id,
        'status':
        'partial' if actors else 'unsupported',
        'execution_model':
        'AIC_AIV_actors',
        'artifacts':
        evidence,
        'actors':
        actors,
        'sites':
        sites,
        'source_associations':
        associations,
        'source_origin_associations':
        origin_associations,
        'loops':
        loops,
        'global_arguments':
        pointers,
        'workspace':
        [item for item in pointers if item['role'] == 'workspace'],
        'dependencies':
        dependencies,
        'static_readiness':
        static_readiness,
        'compiler_provenance':
        provenance,
        'resources': {
            'basis': 'compiler_metadata',
            'values': dict(compiler_metadata),
            'measured': False
        },
        'limitations': [
            'Final actor LLVM must be supplied by an actual compiler output hook; ttadapter is pre actor expansion.',
            'Unknown actor type, workspace role and source identity remain unknown.',
            'Typed same-compile HIVM readiness channels are static actor relations; encoded LLVM sites and dynamic generations are not paired by name, order or time.',
            'CFG cycles and phi expressions are static; occurrences and buffer rotation are not inferred.',
            'Issue/readiness/barrier sites are compiler evidence, not engine busy intervals.'
        ]
    }
