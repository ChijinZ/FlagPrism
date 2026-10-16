"""Actual compiler-site mapping and strict GCU census transport validation.

Cells count reached source control boundaries, including masked operations whose
mask is entirely false. They do not measure productive lanes or time.
"""
import hashlib
import math
import struct

LAYOUT = 'gcu_site_census_v1'
CELL_STRIDE = 64
HEADER_BYTES = 32


def compiler_sites(plan):
    from .automatic_plan import _source_line
    inventory = {row['opId']: row for row in plan['inventory']}
    sites = []
    for identity in plan['selected_sites']:
        row = inventory[identity]
        operation = row['mlirOpName']
        result = row.get('result', {})
        dtype = result.get('elementDtype', '')
        from .automatic_plan import _is_data_candidate
        data = _is_data_candidate(row)
        repeating_data = any(
            _is_data_candidate(inventory[site]) and any(
                owner.get('repeated')
                for owner in inventory[site].get('controlFlowAncestors', []))
            for site in plan['selected_sites'])
        primary = (data and row.get('selection_reason')
                   != 'verified_kernel_entry_scalar_context'
                   and (not repeating_data or any(
                       owner.get('repeated')
                       for owner in row.get('controlFlowAncestors', []))))
        line = _source_line(row)
        sites.append({
            'site': identity,
            'role': 'primary' if primary else 'context',
            'operation': operation,
            'value_kind': result.get('valueKind'),
            'element_dtype': dtype,
            'origin': {
                'kind':
                'automatic_compiler_operation',
                'source_loc':
                row.get('sourceLoc'),
                'source_locations': ([{
                    'file': line[0],
                    'line': line[1]
                }] if line else []),
                'control_flow_ancestors':
                row.get('controlFlowAncestors', []),
            },
        })
    return sites


def validate_transport(raw, *, programs, sites):
    """Validate the backend's physical header/padding before generic decoding."""
    cells = programs * sites
    expected = HEADER_BYTES + cells * CELL_STRIDE
    if len(raw) != expected:
        raise ValueError(
            'GCU census transport length contradicts actual grid/sites')
    header = struct.unpack_from('<8I', raw)
    if header != (0, cells, 0, 0, CELL_STRIDE, expected, 0, 0):
        raise ValueError('GCU census transport header contradicts descriptor')
    for offset in range(HEADER_BYTES, expected, CELL_STRIDE):
        count, flags = struct.unpack_from('<II', raw, offset)
        if (flags & ~3 or bool(flags & 1) != bool(count)
                or flags & 2 and count != 0xffffffff
                or any(raw[offset + 8:offset + CELL_STRIDE])):
            raise ValueError(
                'GCU census cell flags/count/padding are inconsistent')
    return dict(
        zip(('write_idx', 'capacity', 'overflow_count', 'flags', 'record_size',
             'payload_offset', 'reserved0', 'reserved1'), header))


def attach_export(exported_run, metadata):
    raw = bytes(exported_run['raw_buffer'])
    runtime = exported_run['runtime_metadata']
    grid = runtime.get('grid')
    if not isinstance(grid, (list, tuple)) or not 1 <= len(grid) <= 3:
        raise ValueError('GCU census requires actual launch grid')
    grid = list(grid) + [1] * (3 - len(grid))
    if any(type(n) is not int or n <= 0 for n in grid):
        raise ValueError('GCU census grid must contain positive dimensions')
    programs = math.prod(grid)
    sites = metadata['debug_census_sites']
    if len(sites) != runtime['records_per_instance']:
        raise ValueError(
            'GCU census compiler columns contradict runtime stride')
    if (programs * len(sites) > metadata['debug_max_census_cells']
            or len(raw) > metadata['debug_max_census_bytes']):
        raise ValueError('GCU census export exceeds admitted cell/byte budget')
    header = validate_transport(raw, programs=programs, sites=len(sites))
    descriptor = {
        'schema': 'flagprism.source-census',
        'version': 1,
        'cell_size': 8,
        'byte_order': 'little',
        'grid': grid,
        'program_count': programs,
        'sites': sites,
        'actors': [{
            'kind': 'logical_work_item',
            'id': 0
        }],
        'cells_offset': HEADER_BYTES,
        'program_stride': len(sites) * CELL_STRIDE,
        'actor_stride': len(sites) * CELL_STRIDE,
        'site_stride': CELL_STRIDE,
        'raw_sha256': hashlib.sha256(raw).hexdigest(),
        'backend': 'enflame',
        'record_layout': LAYOUT,
        'count_semantics':
        'source_control_visit_count_including_all_false_masks',
        'program_policy': 'all_grid_census',
        'max_census_cells': metadata['debug_max_census_cells'],
        'max_census_bytes': metadata['debug_max_census_bytes'],
    }
    runtime['source_census_request'] = dict(metadata['debug_census_request'])
    runtime['source_census_compiler_options'] = metadata.get(
        'instrumentation_mode')
    exported_run['source_census'] = {'descriptor': descriptor}
    exported_run['debug_tracked_table'] = metadata.get('debug_tracked_table',
                                                       [])
    exported_run['debug_kernel_name'] = metadata.get('debug_kernel_name',
                                                     metadata.get('name', ''))
    exported_run['decoded'] = {'header': header, 'records': []}
    exported_run['capture_status'] = 'decoded'
    return exported_run
