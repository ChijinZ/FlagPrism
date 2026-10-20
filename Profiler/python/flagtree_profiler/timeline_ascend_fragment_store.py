"""Automatic retained actor indexing and offline fragment-path recomputation."""
import base64
import json
from pathlib import Path
import re
import subprocess
import time

from .timeline_events_ascend import compiler_actors
from .timeline_store import (bundle_path, export_lock, json_bytes, persist,
                             read_artifact, sha256)


def _need(value, message):
    if not value:
        raise ValueError(message)


def _context(capture):
    compiler = capture['metadata']['compiler_metadata']
    compiler_actors(compiler)
    binary = capture['owner']['binary_id']
    _need(
        type(binary) is str and re.fullmatch(r'[0-9a-f]{64}', binary),
        'Invalid fragment binary identity')
    _need(binary == compiler['hash'],
          'Fragment compiler/launch identity differs')
    plan = compiler['debug_automatic_plan']
    selected = [row['opId'] for row in plan['inventory'] if row['selected']]
    return compiler, selected, 'analysis/ascend-fragments/' + binary


def load_fragment_paths(directory, capture, *, retain=None):
    """Recompute facts from retained indexed inputs; never execute an SDK/tool.

    Saved analysis status/member selections are not authority. The lossless
    input closure binds both actual actor inputs, index outputs and tool hash.
    """
    from . import timeline_ascend_fragments, timeline_ascend_regions
    compiler, selected, prefix = _context(capture)

    def read(name, *, digest=None, limit=32 * 1024 * 1024):
        raw = read_artifact(directory, name, limit=limit)
        _need(digest is None or sha256(raw) == digest,
              'Retained fragment input changed: ' + name)
        if retain is not None:
            retain(name, digest=sha256(raw), size=len(raw))
        return raw

    header = json.loads(read(prefix + '/inputs.json', limit=1024 * 1024))
    artifacts = compiler['flagprism_ascend_handoff']['artifacts']
    _need(
        type(header) is dict and header.get('schema_version') == 1
        and header.get('model') == 'ascend.retained_actor_indices.v1'
        and header.get('binary_id') == capture['owner']['binary_id']
        and type(header.get('tool_sha256')) is str
        and re.fullmatch(r'[0-9a-f]{64}', header['tool_sha256'])
        and type(header.get('artifacts')) is list
        and len(header['artifacts']) == len(artifacts),
        'Fragment index header differs from actual compilation')
    reports = []
    for number, artifact in enumerate(artifacts):
        indexed = header['artifacts'][number]
        graphs = {}
        for kind in ('original', 'adapted'):
            spec = artifact['original_input' if kind ==
                            'original' else 'adapted']
            source = (base64.b64decode(spec['data'], validate=True)
                      if kind == 'original' else spec['llir'].encode())
            row = indexed[kind]
            _need(
                sha256(source) == spec['sha256'] == row['input_sha256'],
                'Fragment source differs from compiled actor')
            input_name = prefix + '/' + str(number) + '.' + kind + '.ll'
            graph_name = prefix + '/' + str(number) + '.' + kind + '.stdout'
            _need(
                read(input_name, digest=spec['sha256'],
                     limit=16 * 1024 * 1024) == source,
                'Indexed actor bytes differ from compiler input')
            graphs[kind] = json.loads(
                read(graph_name, digest=row['graph_sha256']))
            _need(type(graphs[kind]) is dict, 'Invalid retained actor index')
        for actor in artifact['metadata']['actors']:
            roles = [
                r['final_formal_index'] for r in actor['argument_roles']
                if r.get('role') == 'dynamic_trace'
            ]
            _need(len(roles) == 1, 'Missing unique actor trace role')
            reports.append(
                timeline_ascend_fragments.bind_fragment_paths(
                    graphs['original'],
                    graphs['adapted'],
                    manifest=artifact['metadata'],
                    function=actor['function'],
                    trace_argument_index=roles[0],
                    original_input_sha256=artifact['original_input']['sha256'],
                    adapted_input_sha256=artifact['adapted']['sha256'],
                    selected_source_ids=selected))
    rules = {
        module.__name__: sha256(Path(module.__file__).read_bytes())
        for module in (timeline_ascend_fragments, timeline_ascend_regions)
    }
    result = dict(schema_version=1,
                  model='ascend.fragment_path_report.v1',
                  binary_id=capture['owner']['binary_id'],
                  actors=reports,
                  rules_sha256=rules,
                  tool_sha256=header['tool_sha256'],
                  inputs_sha256=sha256(json_bytes(header)),
                  native_schedule_qualified=False,
                  source_value_equivalence_verified=False)
    relative = 'derived/ascend-fragments/' + sha256(
        json_bytes(result)) + '/report.json'
    with export_lock(directory):
        persist(directory, relative, json_bytes(result))
    return dict(status='fragment_paths_recomputed',
                report_file=relative,
                checked_regions=sum(
                    r['status'] == 'llvm_observed_fragment_operations_bound'
                    for a in reports for r in a['regions']),
                total_regions=sum(len(a['regions']) for a in reports),
                native_schedule_qualified=False,
                source_value_equivalence_verified=False)


def inspect_capture_fragments(directory, capture, *, deadline=None):
    """Default optional analysis; failures preserve the original raw capture."""
    status = dict(status='fragment_paths_unavailable',
                  native_schedule_qualified=False)
    try:
        compiler, _, prefix = _context(capture)
        inputs = bundle_path(directory, prefix + '/inputs.json')
        if inputs.exists():
            return load_fragment_paths(directory, capture)
        tool = Path(__file__).parent / 'lib/flagprism-ascend-structure'
        _need(tool.is_file(),
              'Packaged Ascend actor structure reader is unavailable')
        from .timeline_ascend_machine import _run
        target = bundle_path(directory, prefix)
        target.mkdir(parents=True, exist_ok=True)
        commands, indexed = [], []
        stop = time.monotonic() + 20 if deadline is None else deadline
        for number, artifact in enumerate(
                compiler['flagprism_ascend_handoff']['artifacts']):
            entry = {}
            for kind in ('original', 'adapted'):
                spec = artifact['original_input' if kind ==
                                'original' else 'adapted']
                raw = (base64.b64decode(spec['data'], validate=True)
                       if kind == 'original' else spec['llir'].encode())
                _need(
                    len(raw) <= 16 * 1024 * 1024
                    and sha256(raw) == spec['sha256'],
                    'Invalid bounded compiler actor input')
                name = str(number) + '.' + kind
                relative = prefix + '/' + name + '.ll'
                with export_lock(directory):
                    persist(directory, relative, raw)
                graph_raw = _run(tool, [str(bundle_path(directory, relative))],
                                 target, name, stop, commands)
                graph = json.loads(graph_raw)
                _need(
                    graph.get('input_sha256') == spec['sha256'],
                    'Actor index input hash differs')
                entry[kind] = dict(input_sha256=spec['sha256'],
                                   graph_sha256=sha256(graph_raw))
            indexed.append(entry)
        header = dict(schema_version=1,
                      model='ascend.retained_actor_indices.v1',
                      binary_id=capture['owner']['binary_id'],
                      artifacts=indexed,
                      tool_sha256=sha256(tool.read_bytes()))
        with export_lock(directory):
            persist(directory, prefix + '/inputs.json', json_bytes(header))
        return load_fragment_paths(directory, capture)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError,
            RecursionError, subprocess.SubprocessError) as error:
        status.update(reason=str(error), exception=type(error).__name__)
    return status
