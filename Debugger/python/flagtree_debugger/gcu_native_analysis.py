"""Automatic final-image reader/record diagnostics, shared by capture/reinspect.

These finite checks never grant source-region, external-entry, physical-MMIO or
hardware-busy qualification. Unsupported cases remain per-point diagnostics.
"""
import hashlib
import time

from .gcu_native_control import index_direct_control
from .gcu_native_image import bind_instructions
from .gcu_native_values import inspect_inline_reader, inspect_inline_record_fields_auto


def analyze_native(binary, native, *, locations, manifest):
    """Bind every result to actual image bytes and the generated site table."""
    if (type(locations) is not dict
            or type(locations.get('schema_version')) is not int
            or locations.get('schema_version') != 1
            or locations.get('marker_file') != '__flagprism_gcu_clock_v1__'
            or type(locations.get('locations')) is not list
            or len(locations['locations']) > 4096 or type(manifest) is not dict
            or type(manifest.get('sites')) is not list
            or not 0 < len(manifest['sites']) <= 512):
        raise ValueError('Invalid bounded GCU native analysis inputs')
    sites = set()
    for site in manifest['sites']:
        identity = site.get('id')
        if type(identity) is not int or identity <= 0 or identity in sites:
            raise ValueError('Invalid or duplicate GCU analysis site')
        sites.add(identity)
    program = bind_instructions(binary, native)
    instructions = program['instructions']
    graph = index_direct_control(instructions,
                                 start_packet=program['start_packet'],
                                 end_packet=program['end_packet'])
    phases = ('begin_counter', 'end_counter', 'begin_identity', 'end_identity')
    rows, readers, records = [], {}, {}
    seen = set()
    deadline = time.monotonic() + 10
    for point in locations['locations']:
        if type(point) is not dict:
            raise ValueError('Invalid GCU native analysis marker')
        site, phase, pc = point.get('site_id'), point.get('phase'), point.get(
            'address')
        column = point.get('column')
        if (type(site) is not int or site not in sites
                or type(column) is not int or not 1 <= column <= 4
                or phase != phases[column - 1] or type(pc) is not int
                or pc % 16
                or not program['start_packet'] <= pc < program['end_packet']):
            raise ValueError(
                'Native analysis marker differs from actual site/extent')
        key = (site, phase, pc)
        if key in seen:
            raise ValueError('Duplicate native analysis point')
        seen.add(key)
        if column not in (1, 2):
            continue
        row = dict(site_id=site, phase=phase, marker_packet=pc)
        if time.monotonic() > deadline or (pc not in readers
                                           and len(readers) >= 128):
            row['reader'] = dict(status='unverified',
                                 reason='native_analysis_budget_exhausted')
            rows.append(row)
            continue
        if pc not in readers:
            try:
                readers[pc] = inspect_inline_reader(instructions,
                                                    marker_packet=pc,
                                                    control=graph)
            except ValueError as error:
                readers[pc] = dict(status='unverified', reason=str(error))
        row['reader'] = readers[pc]
        if column == 2 and readers[pc]['status'] != 'unverified':
            if pc not in records:
                if time.monotonic() > deadline:
                    records[pc] = dict(
                        status='unverified',
                        reason='native_analysis_budget_exhausted')
                else:
                    try:
                        records[pc] = inspect_inline_record_fields_auto(
                            instructions, marker_packet=pc, control=graph)
                    except ValueError as error:
                        records[pc] = dict(status='unverified',
                                           reason=str(error))
            row['relative_record_fields'] = records[pc]
        rows.append(row)
    return dict(schema_version=1,
                status='finite_native_diagnostics',
                semantics='conditional_reader_and_relative_record_checks',
                budget_kind='cooperative_between_checks',
                elf_sha256=program['elf_sha256'],
                disassembly_sha256=hashlib.sha256(native).hexdigest(),
                kernel_symbol=program['kernel_symbol'],
                points=rows,
                source_region_qualified=False,
                reader_valueflow_qualified=False,
                external_entries_qualified=False,
                hardware_busy_qualified=False,
                direct_control_unknown_count=len(graph['unknown_controls']))
