"""Read source-site visit counts without manufacturing a timeline.

The wire cell is two little-endian u32 words: a saturating visit count and
flags (visited=1, overflow=2). Physical strides are explicit because backend
publishers need different padding. A cell belongs to one logical observer in
one program of one original launch. It says the selected control position was
reached, including a masked operation whose data mask was entirely false.

This module checks bytes and layout, not compiler provenance. The producer
must independently establish the invocation, binary, selected sites and source
mapping. A digest or a compiler-looking descriptor never proves that join.
"""
import copy
import hashlib
import math
import struct

from .observations import observation

SCHEMA = 'flagprism.source-census'
UINT32_MAX = (1 << 32) - 1
VISITED = 1
OVERFLOW = 2
DEFAULT_MAX_CELLS = 1048576
DEFAULT_MAX_BYTES = 8388608


def _uint(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


class CensusReader:
    """Validate the whole capture; query any cell without expanding the matrix.

    Site index and actor index refer to the ordered descriptor arrays; the
    compiler's site and actor IDs are kept separately. Linear program IDs use
    x + grid_x * (y + grid_y * z). Presentation selection never limits capture.
    """

    def __init__(self,
                 raw,
                 descriptor,
                 *,
                 max_cells=DEFAULT_MAX_CELLS,
                 max_bytes=DEFAULT_MAX_BYTES):
        _uint(max_cells, 'max_cells', 1)
        _uint(max_bytes, 'max_bytes', 8)
        if not isinstance(raw, bytes):
            raise ValueError('census raw must be immutable bytes')
        if len(raw) > max_bytes:
            raise ValueError('source census byte budget exceeded')
        if not isinstance(descriptor, dict):
            raise ValueError('census descriptor must be an object')
        desc = copy.deepcopy(descriptor)
        if (desc.get('schema') != SCHEMA
                or type(desc.get('version')) is not int or desc['version'] != 1
                or desc.get('cell_size') != 8
                or type(desc.get('cell_size')) is not int
                or desc.get('byte_order') != 'little'):
            raise ValueError('unsupported source census layout')
        digest = hashlib.sha256(raw).hexdigest()
        if desc.get('raw_sha256') != digest:
            raise ValueError('source census raw SHA256 mismatch')
        grid = desc.get('grid')
        if not isinstance(grid, list) or len(grid) != 3:
            raise ValueError('source census requires a three-dimensional grid')
        for dimension in grid:
            _uint(dimension, 'grid dimension')
        programs = _uint(desc.get('program_count'), 'program_count')
        if programs != math.prod(grid):
            raise ValueError('program count does not match the actual grid')
        sites, actors = desc.get('sites'), desc.get('actors')
        if not isinstance(sites, list) or not sites or len(sites) > 128:
            raise ValueError('source census requires ordered sites')
        if not isinstance(actors, list) or not actors or len(actors) > 1024:
            raise ValueError(
                'source census requires ordered logical observers')
        site_ids = set()
        for site in sites:
            if not isinstance(site, dict):
                raise ValueError('invalid source census site')
            identity = _uint(site.get('site'), 'site')
            if identity in site_ids or site.get('role') not in ('primary',
                                                                'context'):
                raise ValueError('duplicate site or invalid site role')
            site_ids.add(identity)
        actor_ids = set()
        for actor in actors:
            if not isinstance(actor, dict):
                raise ValueError('invalid source census logical observer')
            kind = actor.get('kind')
            identity = _uint(actor.get('id'), 'actor id')
            if kind not in ('logical_warp', 'logical_work_item',
                            'logical_program_observer'):
                raise ValueError('unsupported logical observer kind')
            if (kind, identity) in actor_ids:
                raise ValueError('duplicate logical observer')
            actor_ids.add((kind, identity))
        cells = programs * len(actors) * len(sites)
        if cells > max_cells:
            raise ValueError('source census cell budget exceeded')
        offset = _uint(desc.get('cells_offset'), 'cells_offset')
        site_stride = _uint(desc.get('site_stride'), 'site_stride', 8)
        actor_stride = _uint(desc.get('actor_stride'), 'actor_stride', 8)
        program_stride = _uint(desc.get('program_stride'), 'program_stride', 8)
        if any(value % 4 for value in (offset, site_stride, actor_stride,
                                       program_stride)):
            raise ValueError('source census cells must be u32 aligned')
        actor_extent = (len(sites) - 1) * site_stride + 8
        program_extent = (len(actors) - 1) * actor_stride + actor_extent
        if actor_stride < actor_extent or program_stride < program_extent:
            raise ValueError('overlapping source census cells')
        end = offset if not programs else (offset +
                                           (programs - 1) * program_stride +
                                           program_extent)
        if end > len(raw):
            raise ValueError('truncated source census matrix')
        self.raw = raw
        self._descriptor = desc
        self.program_count = programs
        self._sites = sites
        self._actors = actors
        self._offset = offset
        self._site_stride = site_stride
        self._actor_stride = actor_stride
        self._program_stride = program_stride
        # Validate every raw cell, including programs not selected for display.
        selected = None
        observed_programs = primary_programs = overflow_cells = nonzero_cells = 0
        total_visits = 0
        for program in range(programs):
            seen = primary = False
            for actor_index in range(len(actors)):
                for site_index, site in enumerate(sites):
                    cell = self.cell(program, actor_index, site_index)
                    if cell['count']:
                        seen = True
                        primary |= site['role'] == 'primary'
                        nonzero_cells += 1
                        total_visits += cell['count']
                    overflow_cells += int(cell['overflow'])
            observed_programs += int(seen)
            primary_programs += int(primary)
            if primary and selected is None:
                selected = program
        self._summary = dict(
            program_count=programs,
            cell_count=cells,
            observed_programs=observed_programs,
            primary_observed_programs=primary_programs,
            nonzero_cells=nonzero_cells,
            overflow_cells=overflow_cells,
            retained_visit_sum=total_visits,
            selected_program=selected,
            selection_policy='lowest_program_with_primary_visits',
            selection_is_presentation_only=True,
            mask_activity='unobserved',
            status=('count_overflow'
                    if overflow_cells else 'primary_visits_available'
                    if primary_programs else 'no_primary_visits'))

    @property
    def descriptor(self):
        return copy.deepcopy(self._descriptor)

    @property
    def summary(self):
        return dict(self._summary)

    def cell(self, program, actor_index, site_index):
        """Return a genuine count cell, including unvisited zero cells."""
        for value, size, name in ((program, self.program_count,
                                   'program'), (actor_index, len(self._actors),
                                                'actor_index'),
                                  (site_index, len(self._sites),
                                   'site_index')):
            _uint(value, name)
            if value >= size:
                raise ValueError(f'{name} outside source census matrix')
        offset = (self._offset + program * self._program_stride +
                  actor_index * self._actor_stride +
                  site_index * self._site_stride)
        count, flags = struct.unpack_from('<II', self.raw, offset)
        if (flags & ~(VISITED | OVERFLOW)
                or bool(flags & VISITED) != bool(count)
                or (flags & OVERFLOW and count != UINT32_MAX)):
            raise ValueError('invalid source census count/flags')
        return dict(program=program,
                    actor=copy.deepcopy(self._actors[actor_index]),
                    site=self._sites[site_index]['site'],
                    site_index=site_index,
                    role=self._sites[site_index]['role'],
                    count=count,
                    visited=bool(flags & VISITED),
                    overflow=bool(flags & OVERFLOW),
                    exact=not bool(flags & OVERFLOW),
                    raw_offset=offset)

    def observations(self,
                     program,
                     *,
                     capture_id,
                     invocation_id,
                     binary_id,
                     association_evidence=None,
                     source='source_census'):
        """Return one counter per reached site, never N synthetic intervals."""
        for name, value in (('capture_id', capture_id), ('binary_id',
                                                         binary_id)):
            if not isinstance(value, str) or not value:
                raise ValueError(f'source census requires {name}')
        if invocation_id is not None and (not isinstance(invocation_id, str)
                                          or not invocation_id):
            raise ValueError('invocation_id must be a nonempty string or None')
        if association_evidence is not None and not isinstance(
                association_evidence, dict):
            raise ValueError('association_evidence must be an object or None')
        for name, value in (('binary_id', binary_id), ('invocation_id',
                                                       invocation_id)):
            if name in self._descriptor and self._descriptor[name] != value:
                raise ValueError(
                    f'census {name} does not match launch identity')
        if association_evidence and association_evidence.get(
                'binary_id', binary_id) != binary_id:
            raise ValueError(
                'census evidence binary does not match launch identity')
        if program is None:
            return []
        result = []
        for actor_index in range(len(self._actors)):
            for site_index, site in enumerate(self._sites):
                cell = self.cell(program, actor_index, site_index)
                if not cell['visited']:
                    continue
                compiler = copy.deepcopy(site)
                compiler['kind'] = 'automatic_compiler_operation'
                if compiler.get('binary_id', binary_id) != binary_id:
                    raise ValueError(
                        'census site binary does not match launch identity')
                if compiler.get('scope_id', site['site']) != site['site']:
                    raise ValueError(
                        'census site scope does not match column identity')
                compiler.update(binary_id=binary_id, scope_id=site['site'])
                event = dict(
                    id=
                    f'{capture_id}:census:{program}:{actor_index}:{site["site"]}',
                    source=source,
                    capture_id=capture_id,
                    invocation_id=invocation_id,
                    binary_id=binary_id,
                    semantic='counter',
                    counter_kind='source_control_visit_count',
                    program=program,
                    actor=cell['actor'],
                    site=site['site'],
                    site_role=site['role'],
                    count=cell['count'],
                    value=cell['count'],
                    count_exact=cell['exact'],
                    overflow=cell['overflow'],
                    unit='visits',
                    occurrence=None,
                    iteration=None,
                    clock=None,
                    start_tick=None,
                    end_tick=None,
                    mask_activity='unobserved',
                    storage='source_site_census_v1',
                    raw_offset=cell['raw_offset'],
                    raw_sha256=self._descriptor['raw_sha256'],
                    compiler_site=compiler,
                    source_region_origin=copy.deepcopy(
                        site.get('origin') or {}),
                    association_status=('verified' if invocation_id
                                        and association_evidence else
                                        'unassociated'),
                    association_evidence=copy.deepcopy(association_evidence),
                    limits=[
                        'Counts mean selected source control positions were reached; '
                        'masked data activity and hardware busy time are not measured.',
                        'Only the declared logical observer in each program is counted; '
                        'other lanes or warps are not inferred.',
                    ])
                result.append(observation(event))
        return result


def decode_source_census(raw,
                         descriptor,
                         *,
                         capture_id,
                         invocation_id,
                         binary_id,
                         association_evidence=None,
                         source='source_census',
                         max_cells=DEFAULT_MAX_CELLS,
                         max_bytes=DEFAULT_MAX_BYTES):
    """Validate all cells and present the first program with primary visits.

    The full raw matrix and descriptor must remain in the capture. This bounded
    summary is a display choice, not a claim that other programs were omitted
    by collection. Call CensusReader.observations for another program.
    """
    reader = CensusReader(raw,
                          descriptor,
                          max_cells=max_cells,
                          max_bytes=max_bytes)
    events = reader.observations(reader.summary['selected_program'],
                                 capture_id=capture_id,
                                 invocation_id=invocation_id,
                                 binary_id=binary_id,
                                 association_evidence=association_evidence,
                                 source=source)
    return dict(schema_version=1,
                storage='source_site_census_v1',
                observations=events,
                summary=reader.summary,
                loss=dict(exact=not bool(reader.summary['overflow_cells']),
                          overflow_cells=reader.summary['overflow_cells'],
                          sampling=False,
                          capture_policy='all_grid_census'))
