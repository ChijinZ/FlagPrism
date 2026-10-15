"""Typed SDK HIVM readiness channels; static relations, never dynamic pairing."""
from __future__ import annotations
import hashlib
import re

PRINT_FLAG = '--bishengir-print-ir-after=hivm-graph-sync-solver'
_HEADER = re.compile(
    r'^func\.func\s+@([\w.$]+)\(.*hivm\.func_core_type\s*=\s*#hivm\.func_core_type<(AIC|AIV)>'
)
_SYNC = re.compile(
    r'\bhivm\.hir\.sync_block_(set|wait)\s*\[<(CUBE|VECTOR)>,\s*<(PIPE_\w+)>,\s*<(PIPE_\w+)>\]\s*flag\s*=\s*(\d+)\b'
)
_LOCATION = re.compile(r'"([^"\n]+)":(\d+):(\d+)')


def build_static_readiness(capture, artifacts):
    """Require the retained same-compile SDK stream and actor LLVM inventory."""
    result = {
        'schema_version': 1,
        'state': 'unavailable',
        'channels': [],
        'sites': [],
        'semantics': 'compiler_static_readiness_not_dynamic_generation',
        'clock_alignment': 'not_established'
    }
    if not isinstance(capture, dict):
        result['reason'] = 'missing_sdk_ir_capture'
        return result
    receipt = capture.get('receipt', {})
    text = capture.get('stderr', '')
    stream = receipt.get('streams', {}).get('stderr', {})
    if (receipt.get('state') != 'finished' or receipt.get('returncode') != 0
            or not receipt.get('compile_id')
            or PRINT_FLAG not in receipt.get('command', [])
            or stream.get('truncated') is not False
            or not isinstance(text, str) or hashlib.sha256(
                text.encode()).hexdigest() != stream.get('sha256')):
        result['reason'] = 'incomplete_or_mismatched_sdk_ir_capture'
        return result
    result['sdk_ir_sha256'] = stream['sha256']
    result['compile_id'] = receipt['compile_id']
    result['source_ir_sha256'] = receipt.get('source_ir_sha256')
    actors = {}
    for artifact in artifacts:
        if (artifact.get('driver_job', {}).get('state') != 'finished'
                or artifact['driver_job'].get('compile_id')
                != receipt['compile_id']
                or not isinstance(artifact.get('llir'), str)
                or hashlib.sha256(artifact['llir'].encode()).hexdigest()
                != artifact.get('sha256')
                or artifact.get('metadata', {}).get('module_sha256')
                != artifact.get('sha256')):
            continue
        for actor in artifact.get('metadata', {}).get('actors', []):
            key = (actor.get('function'), actor.get('actor_kind'))
            actors.setdefault(key, []).append({
                'module_sha256':
                artifact['metadata'].get('module_sha256'),
                'artifact_sha256':
                artifact.get('sha256'),
                'adapted_sha256':
                artifact.get('adapted', {}).get('sha256')
            })
    actor = None
    saw_pass = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if 'IR Dump' in line:
            saw_pass = 'IR Dump After GraphSyncSolver (hivm-graph-sync-solver)' in line
            actor = None
        if line.startswith('func.func ') or line == '}':
            actor = None
        match = _HEADER.match(line)
        if match:
            actor = (match[1], match[2])
        match = _SYNC.search(line)
        if not match or actor is None or not saw_pass:
            continue
        kind, core, producer, consumer, flag = match.groups()
        expected = 'AIC' if core == 'CUBE' else 'AIV'
        entries = actors.get(actor, [])
        site = {
            'id':
            'hivm:' + stream['sha256'] + ':' + str(line_number),
            'operation':
            'sync_block_' + kind,
            'function':
            actor[0],
            'actor_kind':
            actor[1],
            'native_core':
            core,
            'producer_pipeline':
            producer,
            'consumer_pipeline':
            consumer,
            'flag_id':
            int(flag),
            'dump_line':
            line_number,
            'source_locations': [{
                'file': f,
                'line': int(n),
                'column': int(c)
            } for f, n, c in _LOCATION.findall(line)],
            'source_cost_ownership':
            'not_established',
            'raw_ir':
            line.strip(),
            'actor_artifacts':
            entries,
            'state':
            'verified_same_compile_actor' if len(entries) == 1
            and expected == actor[1] else 'unassociated_actor'
        }
        result['sites'].append(site)
    groups = {}
    for site in result['sites']:
        groups.setdefault((site['flag_id'], site['producer_pipeline'],
                           site['consumer_pipeline']), []).append(site)
    for (flag, producer, consumer), sites in groups.items():
        sets = [
            site for site in sites if site['operation'] == 'sync_block_set'
            and site['state'] == 'verified_same_compile_actor'
        ]
        waits = [
            site for site in sites if site['operation'] == 'sync_block_wait'
            and site['state'] == 'verified_same_compile_actor'
        ]
        if len(sets) == 1 and len(waits) == 1 and sets[0][
                'actor_kind'] != waits[0]['actor_kind']:
            result['channels'].append({
                'id':
                'hivm-channel:' + stream['sha256'] + ':' + str(flag) + ':' +
                producer + ':' + consumer,
                'state':
                'compiler_static',
                'producer_site_id':
                sets[0]['id'],
                'consumer_site_id':
                waits[0]['id'],
                'producer_function':
                sets[0]['function'],
                'consumer_function':
                waits[0]['function'],
                'producer_actor_kind':
                sets[0]['actor_kind'],
                'consumer_actor_kind':
                waits[0]['actor_kind'],
                'flag_id':
                flag,
                'producer_pipeline':
                producer,
                'consumer_pipeline':
                consumer,
                'dynamic_generation':
                None,
                'dynamic_pairing':
                'not_established'
            })
    result['state'] = 'compiler_static' if result[
        'channels'] else 'partial' if saw_pass else 'unavailable'
    if not result['channels']:
        result[
            'reason'] = 'no_unique_cross_actor_typed_channel' if saw_pass else 'sdk_pass_dump_not_emitted'
    return result
