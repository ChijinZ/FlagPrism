"""A bounded thread view of complete native late raw, using the common schema.

The entire capture is validated before choosing displayed actors. Full raw and
collective footprints remain available; this projection does not reduce device
instrumentation or certify source cost, clock alignment or hardware busy time.
"""
from collections import defaultdict
from pathlib import Path

from .timeline_events import stable_id, validate_raw_batch
from .timeline_nvidia_late_raw import decode_late_raw


def canonicalize_late_capture(raw, *, owner, metadata, actor_indices=None):
    identity = {
        key: owner.get(key)
        for key in ('capture_id', 'invocation_id', 'binary_id')
    }
    if any(type(value) is not str or not value for value in identity.values()):
        raise ValueError('Actual late capture identity is required')
    namespace = tuple(identity[key]
                      for key in ('capture_id', 'invocation_id', 'binary_id'))
    plan, layout = owner.get('plan'), owner.get('layout')
    if (not isinstance(plan, dict) or not isinstance(layout, dict)
            or plan.get('binary_id') != identity['binary_id']
            or metadata.get('binary_id') != identity['binary_id']
            or layout.get('storage_version') != 'nvidia-late-1'
            or layout.get('raw_bytes') != len(raw)):
        raise ValueError('Late view binary/layout binding differs')
    compiled = metadata.get('compiler_metadata') or {}
    original_plan = compiled.get('flagprism_late_manifest')
    if (not isinstance(original_plan, dict) or {
            key: value
            for key, value in plan.items() if key != 'binary_id'
    } != original_plan or metadata.get('automatic_plan') != plan):
        raise ValueError(
            'Late owner plan differs from the actual compiled manifest')
    if (owner.get('submission_outcome') != 'returned'
            or owner.get('readback_integrity', {}).get('status') != 'passed'):
        raise ValueError(
            'Late canonical view requires returned submission and validated readback'
        )
    from .timeline_nvidia_late_storage import plan_late_storage
    expected = plan_late_storage(plan,
                                 grid=layout.get('grid'),
                                 scratch_size=layout.get('scratch_size'),
                                 alignment=layout.get('alignment'),
                                 num_ctas=layout.get('num_ctas'))
    if [list(slot) for slot in expected['slots']
        ] != [list(slot) for slot in layout.get('slots', [])]:
        raise ValueError(
            'Late view program slots contradict actual launch geometry')
    decoded = decode_late_raw(plan, raw, slots=layout['slots'])
    actors = plan['actors']
    if actor_indices is None:
        actor_indices = tuple(range(min(4, actors)))
    if (type(actor_indices) not in (tuple, list)
            or not 1 <= len(actor_indices) <= 4 or any(
                type(v) is not int or not 0 <= v < actors
                for v in actor_indices)
            or len(set(actor_indices)) != len(actor_indices)):
        raise ValueError(
            'Late canonical view requires one to four distinct actual thread indices'
        )
    grid = layout.get('grid')
    if type(grid) not in (tuple, list) or len(grid) != 3 or any(
            type(v) is not int or v <= 0 for v in grid):
        raise ValueError('Actual nonempty launch geometry is required')
    artifact_by_path = {
        str(Path(row['path'])): row['sha256']
        for row in metadata.get('timeline_artifacts', [])
    }
    presentation = {
        'global_load_issue_bracket':
        ('Global-memory load', 'Global memory issue'),
        'global_store_issue_bracket':
        ('Global-memory store', 'Global memory issue'),
        'global_atomic_issue_bracket':
        ('Global-memory atomic', 'Global memory issue'),
        'shared_load_native_bracket':
        ('Shared-memory load', 'Shared memory issue'),
        'shared_load_issue_bracket': ('Shared matrix load',
                                      'Shared memory issue'),
        'shared_store_after': ('Shared-memory store observed',
                               'Shared memory checkpoints'),
        'copy_submit_after': ('Async copy submitted', 'Async copy submission'),
        'commit_after': ('Async group committed', 'Async copy submission'),
        'wait_bracket': ('Async wait', 'Async wait'),
        'matrix_issue_bracket': ('Matrix instruction group', 'Matrix issue'),
        'compute_issue_bracket': ('Compute instruction group',
                                  'Compute issue'),
        'cta_barrier_after': ('CTA barrier passed', 'CTA checkpoints'),
        'opaque_native_issue_bracket': ('Opaque native instruction',
                                        'Unclassified native'),
        'control_checkpoint': ('Control-flow checkpoint',
                               'Control checkpoints')
    }

    native_sites = {site['site_id']: site for site in plan['sites']}
    sources, sites, site_by_native = {}, [], {}
    for candidate in plan['sites']:
        native = candidate['site_id']
        site_id = stable_id((identity['binary_id'], ), 'site', str(native))
        semantic = ('wait_bracket' if candidate['kind'] == 'wait_bracket' else
                    'completion_checkpoint' if candidate['kind']
                    == 'cta_barrier_after' else 'issue_interval')
        refs = []
        for member in candidate.get('members', []):
            path = str(Path(member.get('directory') or '') /
                       member['file']) if member.get('file') else None
            digest = artifact_by_path.get(path)
            location = dict(file=member.get('file'),
                            directory=member.get('directory'),
                            line=member.get('line'),
                            column=member.get('column'),
                            native_operation=member.get('native_operation'))
            source_id = stable_id((), 'source', digest, location)
            sources[source_id] = dict(
                id=source_id,
                source_sha256=digest,
                relation='compiler_origin_navigation',
                location=location,
                provenance='actual_late_compiler_member_navigation')
            if source_id not in refs:
                refs.append(source_id)
        label, group = presentation.get(
            candidate['kind'], (candidate['kind'], 'Unclassified native'))
        site = dict(id=site_id,
                    name=label + ' [site ' + str(native) + ']',
                    semantic=semantic,
                    source_ids=refs,
                    backend_site_id=str(native),
                    attributes={
                        'display.track_group': group,
                        'nvidia.late_kind': candidate['kind'],
                        'nvidia.native_members': candidate.get('members', []),
                        'nvidia.record_semantics':
                        candidate['record_semantics']
                    })
        sites.append(site)
        site_by_native[native] = site
    observers, records, events, backend_map = [], [], [], {}
    for program in decoded['programs']:
        logical = program['program_id']
        if logical >= grid[0] * grid[1] * grid[2]:
            raise ValueError('Decoded late program exceeds actual launch')
        coordinates = [
            logical % grid[0], (logical // grid[0]) % grid[1],
            logical // (grid[0] * grid[1])
        ]
        for actor_index in actor_indices:
            actor = program['observers'][actor_index]
            kind, local_id = 'nvidia.recording_thread', str(actor_index)
            observer_id = stable_id(namespace, 'observer', kind, local_id,
                                    coordinates)
            complete = bool(decoded['complete'] and actor['complete'])
            sequence, occurrences = 0, defaultdict(int)
            for row in actor['events']:
                site = site_by_native[row['site_id']]
                instant = native_sites[row['site_id']][
                    'record_semantics'] == 'observer_checkpoint_after'
                points = [
                    ('point', row['end_tick'], row['raw_end_offset_bytes'])
                ] if instant else [('entry', row['begin_tick'],
                                    row['raw_begin_offset_bytes']),
                                   ('exit', row['end_tick'],
                                    row['raw_end_offset_bytes'])]
                refs = []
                for phase, tick, offset in points:
                    record_id = stable_id(namespace, 'record', observer_id,
                                          sequence)
                    records.append(
                        dict(id=record_id,
                             observer_id=observer_id,
                             site_id=site['id'],
                             phase=phase,
                             tick=tick,
                             sequence=sequence,
                             offset=offset,
                             length=8))
                    backend_map[stable_id(namespace, 'late-raw-endpoint',
                                          logical, actor_index,
                                          row['occurrence'],
                                          phase)] = record_id
                    refs.append(record_id)
                    sequence += 1
                occurrence = occurrences[site['id']]
                occurrences[site['id']] += 1
                events.append(
                    dict(id=stable_id(namespace, 'event', *refs),
                         observer_id=observer_id,
                         site_id=site['id'],
                         semantic=site['semantic'],
                         kind='instant' if instant else 'interval',
                         start_tick=row['end_tick']
                         if instant else row['begin_tick'],
                         end_tick=None if instant else row['end_tick'],
                         occurrence=occurrence,
                         occurrence_basis='complete_boundary_order'
                         if complete else 'retained_boundary_order',
                         iteration_id=None,
                         record_ids=refs,
                         missing_reason=None,
                         coverage={
                             'nvidia.raw_ordinal':
                             row['occurrence'],
                             'nvidia.payload':
                             row['payload'],
                             'nvidia.raw_tag_offset_bytes':
                             row['raw_tag_offset_bytes'],
                             'nvidia.raw_payload_offset_bytes':
                             row['raw_payload_offset_bytes']
                         }))
            observers.append(
                dict(id=observer_id,
                     kind=kind,
                     local_id=local_id,
                     program_coordinates=coordinates,
                     clock_domain_id=stable_id(namespace,
                                               'unverified-observer-domain',
                                               logical, actor_index),
                     epoch_id=stable_id(namespace, 'capture-epoch-unverified',
                                        logical, actor_index),
                     timer_bits=64,
                     complete=complete,
                     overwritten_records=0,
                     saturated=actor['overflow'],
                     written_records=sequence,
                     retained_records=sequence,
                     physical_identity=None,
                     attributes={
                         'nvidia.logical_program': logical,
                         'nvidia.thread_flat_index': actor_index,
                         'nvidia.capture_actor_count': actors,
                         'nvidia.capture_complete': decoded['complete'],
                         'nvidia.view_actor_indices': list(actor_indices),
                         'nvidia.arrived': actor['arrived'],
                         'nvidia.overflow': actor['overflow']
                     }))
    return validate_raw_batch(
        dict(
            schema_version=1,
            identity=identity,
            raw_artifact=dict(sha256=decoded['raw_sha256'], bytes=len(raw)),
            clock_status='unverified',
            boundary_status='unverified',
            sources=list(sources.values()),
            sites=sites,
            observers=observers,
            records=records,
            events=events,
            backend_record_map={'nvidia.late_rows.v1': backend_map},
            complete=decoded['complete'],
            notes=[
                'Canonical view contains explicitly selected actual thread indices '
                + str(list(actor_indices)) + ' out of ' + str(actors) +
                ' recorded threads per selected program.',
                'Full raw was validated before projection and remains available for other thread views/collective footprints.',
                'Display selection does not reduce instrumentation work or hide loss outside the displayed actors.',
                'Checkpoint duplicate begin words are the same captured read; only the actual end-word slot is referenced.',
                'Source members provide navigation; occurrence is retained native observation order, not a proven loop iteration.',
                'Clock units/alignment, final boundaries, source cost and hardware busy remain unqualified.'
            ]))
