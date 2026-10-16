"""Ascend census transport, separate from the legacy actor event-log ABI.

A shared raw allocation contains three compiler-actor slots per actual source
program. Reserved cells are padding, never synthetic unvisited source sites.
This module validates transport; the late compiler must separately establish
source-program coordinates, site identity and actor ownership.
"""
from __future__ import annotations

import hashlib
import copy
import math
import struct

LAYOUT = 'ascend_source_census_v1'
COMPACT_LAYOUT = 'ascend_source_census_v2'
ALIGNED_LAYOUT = 'ascend_source_census_v3'
CACHE_LINE_BYTES = 64
HEADER_BYTES = 32
ACTOR_SLOTS = 3
RESERVED_SITES = 128
CELL_BYTES = 8
ACTOR_STRIDE = RESERVED_SITES * CELL_BYTES
PROGRAM_STRIDE = ACTOR_SLOTS * ACTOR_STRIDE


def plan_layout(grid,
                *,
                max_cells=1048576,
                max_bytes=8388608,
                version=1,
                site_count=None):
    """Check physical reserved cells and bytes before any device allocation."""
    if not isinstance(grid, (list, tuple)) or not 1 <= len(grid) <= 3:
        raise ValueError(
            'Ascend census requires an actual one-to-three dimensional grid')
    grid = list(grid) + [1] * (3 - len(grid))
    if any(type(value) is not int or value < 0 for value in grid):
        raise ValueError(
            'Ascend census grid dimensions must be nonnegative integers')
    for value, name in ((max_cells, 'max_cells'), (max_bytes, 'max_bytes')):
        if type(value) is not int or value <= 0:
            raise ValueError(f'{name} must be a positive integer')
    if type(version) is not int or version not in (1, 2, 3):
        raise ValueError('unsupported Ascend census physical version')
    if version == 1:
        if site_count is not None and (type(site_count) is not int
                                       or site_count != RESERVED_SITES):
            raise ValueError(
                'Ascend census v1 requires its original 128-column stride')
        columns = RESERVED_SITES
    else:
        if type(site_count
                ) is not int or not 1 <= site_count <= RESERVED_SITES:
            raise ValueError(
                'Ascend census v2 requires actual compiler site_count in 1..128'
            )
        columns = site_count
    actor_stride = columns * CELL_BYTES
    header_bytes = HEADER_BYTES
    if version == 3:
        header_bytes = CACHE_LINE_BYTES
        actor_stride = ((actor_stride + 63) // 64) * 64
    program_stride = ACTOR_SLOTS * actor_stride
    programs = math.prod(grid)
    size = header_bytes + programs * program_stride
    # V3 budgets include every header and actor padding cell.
    cells = size // CELL_BYTES if version == 3 else programs * ACTOR_SLOTS * columns
    if cells > max_cells:
        raise ValueError(
            'Ascend census physical reserved cell budget exceeded')
    if size > max_bytes:
        raise ValueError('Ascend census physical byte budget exceeded')
    return dict(layout=LAYOUT if version == 1 else
                COMPACT_LAYOUT if version == 2 else ALIGNED_LAYOUT,
                version=version,
                grid=grid,
                program_count=programs,
                reserved_cell_count=cells,
                byte_count=size,
                header_bytes=header_bytes,
                actor_slots=ACTOR_SLOTS,
                reserved_sites=columns,
                program_stride=program_stride,
                actor_stride=actor_stride,
                site_stride=CELL_BYTES)


def validate_transport(raw, plan, actor_sites):
    """Require all padding and unassigned compiler slots to remain zero.

    actor_sites maps actual emitted actor slots to ordered, selected compiler
    sites. It is not inferred from which cells happen to contain data.
    """
    expected = plan_layout(plan['grid'],
                           max_cells=plan['reserved_cell_count'] or 1,
                           max_bytes=plan['byte_count'],
                           version=plan['version'],
                           site_count=plan['reserved_sites'])
    if plan != expected:
        raise ValueError(
            'Ascend census plan disagrees with the versioned physical ABI')
    if not isinstance(raw, bytes) or len(raw) != plan['byte_count']:
        raise ValueError(
            'Ascend census raw length disagrees with the actual grid')
    if any(raw[:plan['header_bytes']]):
        raise ValueError(
            'Ascend census reserved header must be zero; legacy ring headers are invalid'
        )
    if not isinstance(actor_sites, dict):
        raise ValueError(
            'Ascend census requires explicit compiler actor columns')
    for slot, sites in actor_sites.items():
        if type(slot) is not int or not 0 <= slot < ACTOR_SLOTS:
            raise ValueError(
                'Ascend census actor slot is outside the physical ABI')
        if not isinstance(sites, list) or not sites or len(
                sites) > plan['reserved_sites']:
            raise ValueError(
                'Ascend census selected compiler sites exceed the reserved stride'
            )
        identities = [site.get('site') for site in sites]
        if (any(
                type(identity) is not int or identity < 0
                for identity in identities)
                or len(set(identities)) != len(identities)):
            raise ValueError(
                'Ascend census compiler site columns are invalid or duplicated'
            )
        columns = [
            site.get('column', index) for index, site in enumerate(sites)
        ]
        if (any(
                type(column) is not int
                or not 0 <= column < plan['reserved_sites']
                for column in columns) or len(set(columns)) != len(columns)):
            raise ValueError(
                'Ascend census emitted columns are invalid or duplicated')
        if any(
                site.get('role') not in ('primary', 'context')
                for site in sites):
            raise ValueError(
                'Ascend census site needs an explicit primary/context role')
    for program in range(plan['program_count']):
        for slot in range(ACTOR_SLOTS):
            selected = {
                site.get("column", index)
                for index, site in enumerate(actor_sites.get(slot, []))
            }
            base = plan['header_bytes'] + program * plan[
                'program_stride'] + slot * plan['actor_stride']
            for column in range(plan['reserved_sites']):
                count, flags = struct.unpack_from('<II', raw,
                                                  base + column * CELL_BYTES)
                if column not in selected:
                    if count or flags:
                        raise ValueError(
                            'Ascend census unassigned actor/site padding contains data'
                        )
                elif (flags & ~3 or bool(flags & 1) != bool(count)
                      or flags & 2 and count != 0xffffffff):
                    raise ValueError(
                        'Ascend census cell count/flags are inconsistent')
            tail = base + plan['reserved_sites'] * CELL_BYTES
            if any(raw[tail:base + plan['actor_stride']]):
                raise ValueError(
                    'Ascend census actor alignment padding contains data')
    return dict(raw_sha256=hashlib.sha256(raw).hexdigest(), **plan)


def actor_descriptor(raw,
                     plan,
                     *,
                     slot,
                     sites,
                     compiler_actor,
                     max_cells=1048576,
                     max_bytes=8388608):
    """Reference shared bytes with actor-qualified columns, without copying raw.

    Call validate_transport once with every actor's selected sites before using
    these descriptors. Source-program and compiler provenance are required
    separately by the capture producer; hashes here establish byte integrity.
    """
    if type(slot) is not int or not 0 <= slot < ACTOR_SLOTS:
        raise ValueError('invalid Ascend census actor slot')
    expected_kind = 'AIC' if slot == 0 else 'AIV'
    if (not isinstance(compiler_actor, dict)
            or compiler_actor.get('kind') != expected_kind
            or compiler_actor.get('runtime_slot') != slot):
        raise ValueError(
            'Ascend census actor type does not match its emitted runtime slot')
    if not sites:
        raise ValueError("Ascend descriptor requires actual emitted sites")
    columns = [site.get('column', index) for index, site in enumerate(sites)]
    if columns != list(range(columns[0], columns[0] + len(columns))):
        raise ValueError('Ascend descriptor needs contiguous actual columns')
    return dict(
        schema='flagprism.source-census',
        version=1,
        cell_size=CELL_BYTES,
        byte_order='little',
        grid=list(plan['grid']),
        program_count=plan['program_count'],
        sites=copy.deepcopy(sites),
        actors=[
            dict(kind='logical_program_observer',
                 id=slot,
                 compiler_actor=copy.deepcopy(compiler_actor))
        ],
        cells_offset=(plan['header_bytes'] + slot * plan['actor_stride'] +
                      columns[0] * CELL_BYTES
                      if plan['program_count'] else plan['header_bytes']),
        program_stride=plan['program_stride'],
        actor_stride=plan['actor_stride'],
        site_stride=CELL_BYTES,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        backend='ascend',
        record_layout=plan['layout'],
        max_census_cells=max_cells,
        max_census_bytes=max_bytes,
        count_semantics='source_control_visit_count_including_all_false_masks')


def decode_shared_census(raw,
                         *,
                         grid,
                         actors,
                         capture_id,
                         invocation_id,
                         binary_id,
                         association_evidence=None,
                         max_cells=1048576,
                         max_bytes=8388608,
                         version=1,
                         site_count=None):
    """Decode actor views over one capture, retaining a single raw reference.

    ``actors`` contains producer-validated slot/sites/compiler_actor entries.
    This consumer does not turn that caller input into a compiler/source proof.
    The same lowest primary-observed program is presented for all actor views.
    """
    from .source_census import CensusReader
    if not isinstance(actors, list) or not actors:
        raise ValueError(
            'Ascend census requires actual compiler actor manifests')
    if any(not isinstance(actor, dict) or type(actor.get('slot')) is not int
           for actor in actors):
        raise ValueError(
            'Ascend census compiler actor entries need integer slots')
    slots = [actor.get('slot') for actor in actors]
    if len(set(slots)) != len(slots):
        raise ValueError('duplicate Ascend census compiler actor slot')
    plan = plan_layout(grid,
                       max_cells=max_cells,
                       max_bytes=max_bytes,
                       version=version,
                       site_count=site_count)
    validate_transport(raw, plan,
                       {actor['slot']: actor['sites']
                        for actor in actors})
    readers, descriptors = [], []
    reader_actors = []
    for actor in actors:
        # A split compiler actor can retain a sparse subset of selected sites.
        # Each view references its exact emitted column; missing columns stay
        # padding and never become synthetic unvisited source operations.
        groups = []
        for index, site in enumerate(actor['sites']):
            site = dict(site, column=site.get('column', index))
            if groups and site['column'] == groups[-1][-1]['column'] + 1:
                groups[-1].append(site)
            else:
                groups.append([site])
        for sites in groups:
            descriptor = actor_descriptor(
                raw,
                plan,
                slot=actor['slot'],
                sites=sites,
                compiler_actor=actor['compiler_actor'],
                max_cells=max_cells,
                max_bytes=max_bytes)
            descriptor.update(raw_ref=dict(capture_id=capture_id,
                                           sha256=descriptor['raw_sha256']),
                              binary_id=binary_id,
                              invocation_id=invocation_id)
            descriptors.append(descriptor)
            readers.append(
                CensusReader(raw,
                             descriptor,
                             max_cells=max_cells,
                             max_bytes=max_bytes))
            reader_actors.append(actor)
    candidates = [
        reader.summary['selected_program'] for reader in readers
        if reader.summary['selected_program'] is not None
    ]
    selected = min(candidates) if candidates else None
    events = []
    for actor, reader in zip(reader_actors, readers):
        observed = reader.observations(
            selected,
            capture_id=capture_id,
            invocation_id=invocation_id,
            binary_id=binary_id,
            association_evidence=association_evidence,
            source='ascend_source_census')
        for event in observed:
            # Each descriptor has one logical observer at actor_index=0;
            # namespace event IDs by its actual runtime slot, without changing
            # invocation, actor, program or compiler site identity.
            event['id'] = (f'{capture_id}:ascend-census:slot{actor["slot"]}:'
                           f'{event["program"]}:{event["site"]}')
            event['actor'] = dict(kind='logical_program_observer',
                                  id=actor['slot'])
            event['compiler_site']['compiler_actor'] = copy.deepcopy(
                actor['compiler_actor'])
        events.extend(observed)
    summaries = [
        dict(actor_slot=actor['slot'], **reader.summary)
        for actor, reader in zip(reader_actors, readers)
    ]
    overflow = sum(item['overflow_cells'] for item in summaries)
    return dict(
        schema_version=1,
        storage=plan['layout'],
        observations=events,
        physical_plan=plan,
        requested_limits=dict(max_census_cells=max_cells,
                              max_census_bytes=max_bytes),
        descriptors=descriptors,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        summary=dict(
            program_count=plan['program_count'],
            reserved_cell_count=plan['reserved_cell_count'],
            physical_byte_count=plan['byte_count'],
            selected_program=selected,
            actors=summaries,
            selection_is_presentation_only=True,
            selection_policy='lowest_program_with_primary_visits',
            transport_visibility=('legacy_ascend_cache_line_hazard'
                                  if version < 3 else 'not_flagged'),
            unknown_loss=version < 3,
            source_program_identity='requires_compiler_producer_evidence'),
        loss=dict(exact=not bool(overflow) and version == 3,
                  transport_visibility=('legacy_ascend_cache_line_hazard'
                                        if version < 3 else 'not_flagged'),
                  unknown_loss=version < 3,
                  overflow_cells=overflow,
                  sampling=False,
                  capture_policy='all_grid_census'))


def compiler_actor_views(handoff, source_sites, *, version=1, site_count=None):
    """Bind emitted marker columns to the exact frontend selection and actor IR.

    The retained LLVM/manifests establish compiler provenance. Actual source
    coordinates come from each marker's own operands, never physical block IDs.
    """
    physical = plan_layout([1], version=version, site_count=site_count)
    if version >= 2 and len(source_sites) != site_count:
        raise ValueError(
            'Ascend census actual frontend selection differs from compiled columns'
        )
    selected = {
        site['site']: (index, site)
        for index, site in enumerate(source_sites)
    }
    if not selected or len(selected) != len(source_sites):
        raise ValueError(
            'Ascend census requires a unique actual frontend site plan')
    actors, occupied = [], set()
    for artifact in handoff.get('artifacts', []):
        manifest = artifact.get('metadata') or {}
        binding = manifest.get('runtime_actor_binding') or {}
        original = artifact.get('llir')
        adapted = (artifact.get('adapted') or {}).get('llir')
        text = artifact.get('manifest_text')
        if not all(
                isinstance(value, str) for value in (original, adapted, text)):
            raise ValueError(
                'Ascend census requires retained original/adapted compiler artifacts'
            )
        original_hash = hashlib.sha256(original.encode()).hexdigest()
        adapted_hash = hashlib.sha256(adapted.encode()).hexdigest()
        manifest_hash = hashlib.sha256(text.encode()).hexdigest()
        import json
        if (json.loads(text) != manifest
                or original_hash != artifact.get('sha256')
                or original_hash != manifest.get('module_sha256') or
                adapted_hash != (artifact.get('adapted') or {}).get('sha256')
                or manifest_hash != artifact.get('manifest_sha256')
                or not handoff.get('compile_id')
                or binding.get('compile_id') != handoff['compile_id']
                or manifest.get('compile_id') != handoff['compile_id']
                or binding.get('module_sha256') != original_hash):
            raise ValueError('Ascend census compiler provenance mismatch')
        kind = binding.get('actor_kind')
        slots = [0] if kind == 'AIC' else [1, 2] if kind == 'AIV' else []
        expression = (dict(
            kind='constant_i64', value=0) if kind == 'AIC' else dict(
                kind='add_i64', call='llvm.hivm.GET.SUBBLOCKID', constant=1))
        source_binding = binding.get('source_program_binding') or {}
        if (not slots or binding.get('layout') != physical['layout']
                or binding.get('header_bytes') != physical['header_bytes']
                or binding.get('admissible_slots') != slots
                or binding.get('expression') != expression
                or binding.get('program_stride_bytes')
                != physical['program_stride'] or
                binding.get('actor_stride_bytes') != physical['actor_stride']
                or binding.get('reserved_columns_per_actor')
                != physical['reserved_sites']
                or source_binding.get('version') != version
                or source_binding.get('basis')
                != 'actual_selected_source_site_marker_operands'
                or source_binding.get('llvm_operand_binding')
                != 'each_marker_actual_def_use_and_dominance'):
            raise ValueError(
                'Ascend census lacks exact emitted actor/coordinate binding')
        entries = [
            entry for entry in manifest.get('actors', [])
            if entry.get('function') == binding.get('function')
            and entry.get('actor_kind') == kind
            and entry.get('dynamic_observation_prepared') is True
        ]
        if len(entries) != 1:
            raise ValueError(
                'Ascend census actual compiler actor is ambiguous')
        emitted = {}
        for marker in manifest.get('dynamic_sites', []):
            identity, column = marker.get('source_op_id'), marker.get(
                'census_column')
            if (identity not in selected or selected[identity][0] != column
                    or (version >= 2
                        and marker.get('source_site_count') != site_count)
                    or marker.get('point_phase') != 'before_source_operation'
                    or marker.get('operation_class')
                    != 'compiler_carried_source_site_marker'):
                raise ValueError(
                    'Ascend census marker is outside the actual frontend selection'
                )
            # Actual SDK clones at this same column contribute to one count.
            emitted[column] = dict(copy.deepcopy(selected[identity][1]),
                                   column=column)
        if not emitted:
            continue
        for slot in slots:
            if slot in occupied:
                raise ValueError(
                    'Ascend census runtime actor slot has multiple compiler owners'
                )
            occupied.add(slot)
            compiler_actor = dict(
                kind=kind,
                runtime_slot=slot,
                id=f'late_llvm:{original_hash}:{binding["function"]}',
                function=binding['function'],
                module_sha256=original_hash,
                compile_id=handoff['compile_id'],
                runtime_actor_binding=copy.deepcopy(binding),
                binding_proof=dict(
                    status='verified_compiler_emission_manifest',
                    manifest_sha256=manifest_hash,
                    original_module_sha256=original_hash,
                    adapted_module_sha256=adapted_hash,
                    source_binding=
                    'actual_frontend_selected_id_column_and_own_marker_operands',
                    cost_attribution='unobserved'))
            actors.append(
                dict(slot=slot,
                     sites=[emitted[key] for key in sorted(emitted)],
                     compiler_actor=compiler_actor))
    if not actors:
        raise ValueError(
            'Ascend census compiler emitted no selected source-site markers')
    return actors
