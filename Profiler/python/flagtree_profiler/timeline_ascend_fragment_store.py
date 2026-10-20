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


def _attach_observations(reports, batch, compiler):
    """Join exact backend site identities; never align different actor clocks."""
    actors = compiler_actors(compiler)
    backend_ids = {}
    for actor in actors.values():
        for sid, site in actor['sites'].items():
            if site['semantic_code'] != 1:
                continue
            key = actor['function'], sid
            identity = site['backend_identity']
            _need(
                backend_ids.setdefault(key, identity) == identity,
                'Ambiguous fragment backend identity')
    sites = {site['backend_site_id']: site for site in batch['sites']}
    _need(
        len(sites) == len(batch['sites']), 'Duplicate canonical backend sites')
    observers = {row['id']: row for row in batch['observers']}
    observations = {}
    for event in batch['events']:
        if event['kind'] != 'interval':
            continue
        key = event['site_id'], event['observer_id']
        observer = observers[event['observer_id']]
        _need(event['end_tick'] >= event['start_tick'],
              'Fragment interval has reversed endpoints')
        row = observations.setdefault(
            key,
            dict(observer_id=observer['id'],
                 program_coordinates=observer['program_coordinates'],
                 clock_domain_id=observer['clock_domain_id'],
                 epoch_id=observer['epoch_id'],
                 timer_bits=observer['timer_bits'],
                 time_unit='raw_counter_ticks',
                 complete=observer['complete'],
                 dropped_records=observer['dropped_records'],
                 interval_count=0,
                 positive_interval_count=0,
                 elapsed_ticks_sum=0,
                 first_tick=event['start_tick'],
                 last_tick=event['end_tick'],
                 first_event_id=event['id'],
                 last_event_id=event['id'],
                 first_record_ids=event['record_ids'],
                 last_record_ids=event['record_ids'],
                 occurrence_basis=event['occurrence_basis'],
                 source_iteration_ids_verified=False))
        row['interval_count'] += 1
        row['positive_interval_count'] += event['end_tick'] > event[
            'start_tick']
        row['elapsed_ticks_sum'] += event['end_tick'] - event['start_tick']
        if event['start_tick'] < row['first_tick']:
            row['first_tick'] = event['start_tick']
            row['first_event_id'] = event['id']
            row['first_record_ids'] = event['record_ids']
        if event['end_tick'] > row['last_tick']:
            row['last_tick'] = event['end_tick']
            row['last_event_id'] = event['id']
            row['last_record_ids'] = event['record_ids']
    for report in reports:
        for region in report['regions']:
            backend_id = backend_ids[report['function'], region['site_id']]
            site = sites[backend_id]
            _need(
                site['attributes'].get(
                    'ascend.source_op_id') == region['source_op_id'],
                'Canonical source operation differs from actor fragment')
            rows = [
                value for (site_id, _), value in observations.items()
                if site_id == site['id']
            ]
            _need(
                all(observers[row['observer_id']]['attributes'].get(
                    'ascend.function') == report['function'] for row in rows),
                'Recorded observer differs from fragment actor')
            region['observations'] = dict(
                status='recorded_intervals' if rows else 'not_observed',
                canonical_site_id=site['id'],
                backend_site_id=backend_id,
                capture_complete=batch['complete'],
                raw_sha256=batch['raw_artifact']['sha256'],
                interval_count=sum(row['interval_count'] for row in rows),
                positive_interval_count=sum(row['positive_interval_count']
                                            for row in rows),
                observers=sorted(rows, key=lambda row: row['observer_id']))


def load_fragment_paths(directory, capture, *, retain=None):
    """Recompute facts from retained indexed inputs; never execute an SDK/tool.

    Saved analysis status/member selections are not authority. The lossless
    input closure binds both actual actor inputs, index outputs and tool hash.
    """
    from . import timeline_ascend_fragments, timeline_ascend_regions, timeline_events_ascend, timeline_ascend_loops
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
    raw = read(capture['raw_file'], digest=capture['raw_sha256'])
    from .timeline_ascend_offline import decode_capture
    batch = decode_capture(capture, raw)
    _attach_observations(reports, batch, compiler)
    rules = {
        module.__name__: sha256(Path(module.__file__).read_bytes())
        for module in (timeline_ascend_fragments, timeline_ascend_regions,
                       timeline_events_ascend, timeline_ascend_loops)
    }
    rules[__name__] = sha256(Path(__file__).read_bytes())
    result = dict(schema_version=2,
                  model='ascend.fragment_path_report.v2',
                  binary_id=capture['owner']['binary_id'],
                  invocation_id=capture['owner']['invocation_id'],
                  capture_id=capture['owner']['capture_id'],
                  raw_sha256=sha256(raw),
                  capture_complete=batch['complete'],
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
                observed_regions=sum(r['observations']['interval_count'] > 0
                                     for a in reports for r in a['regions']),
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
        tool_digest = sha256(tool.read_bytes())
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
                _need(
                    sha256(tool.read_bytes()) == tool_digest,
                    'Actor structure reader changed before execution')
                graph_raw = _run(tool, [str(bundle_path(directory, relative))],
                                 target, name, stop, commands)
                _need(
                    sha256(tool.read_bytes()) == tool_digest,
                    'Actor structure reader changed during execution')
                graph = json.loads(graph_raw)
                _need(
                    type(graph) is dict,
                    'Actor structure reader returned a non-object')
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
                      tool_sha256=tool_digest)
        with export_lock(directory):
            persist(directory, prefix + '/inputs.json', json_bytes(header))
        return load_fragment_paths(directory, capture)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError,
            RecursionError, subprocess.SubprocessError) as error:
        status.update(reason=str(error), exception=type(error).__name__)
    return status
