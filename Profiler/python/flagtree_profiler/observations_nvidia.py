"""Decode inherited Proton NVIDIA ring bytes without fabricated ns conversion.

This adapter adds typed identities and structured truncation to the inherited
per-warp recording ABI. It does not change the underlying recording mechanism.
"""
from __future__ import annotations

import struct


def decode_proton_ring(data: bytes, *, capture_id: str, invocation_id=None,
                       association_evidence=None, scopes=None, granularity='warp', clock_bits=43):
    if not isinstance(data, bytes) or len(data) < 40:
        raise ValueError('Proton ring requires a complete binary header')
    if not isinstance(capture_id, str) or not capture_id:
        raise ValueError('capture_id must identify this buffer capture')
    if clock_bits not in (32, 43):
        raise ValueError('Only declared 32-bit or 43-bit Proton clock encoding is supported')
    if granularity != 'warp':
        raise ValueError('Only the verified per-warp Proton ring ABI is supported')
    version, header_offset, header_size, payload_offset, payload_size, device, blocks, total_units, scratch_size, unit_count = struct.unpack_from('<10I', data)
    if version != 1 or device != 1:
        raise ValueError('Expected version-1 NVIDIA Proton ring')
    if header_offset != 4 or header_size != 40 + unit_count * 4 or payload_offset != header_size:
        raise ValueError('Invalid Proton header offsets')
    if unit_count < 1 or total_units < 1 or unit_count > total_units:
        raise ValueError('Invalid selected warp count')
    if len(data) != payload_offset + payload_size or blocks * scratch_size != payload_size:
        raise ValueError('Truncated or inconsistent Proton payload')
    units = struct.unpack_from('<' + 'I' * unit_count, data, 40)
    if sorted(set(units)) != list(units) or any(unit >= total_units for unit in units):
        raise ValueError('Warp selection must be unique, ordered, and in range')
    scope_names = {int(key): value for key, value in (scopes or {}).items()}
    if any(key < 0 or key > 255 for key in scope_names):
        raise ValueError('Proton ABI masks scope identity to eight bits; larger scope IDs cannot be attributed')
    observations, records, losses, unpaired = [], [], [], []
    for block_index in range(blocks):
        base = payload_offset + block_index * scratch_size
        if base + 16 + total_units * 4 > len(data):
            raise ValueError('Truncated block metadata')
        preamble, program, sm, buffer_size = struct.unpack_from('<4I', data, base)
        if preamble != 0xDEADBEEF:
            raise ValueError('Missing completed block preamble')
        metadata_size = 16 + total_units * 4
        if buffer_size % (unit_count * 8) or buffer_size + metadata_size > scratch_size:
            raise ValueError('Invalid block ring capacity')
        segment_size = buffer_size // unit_count
        capacity = segment_size // 8
        if not capacity:
            raise ValueError('Ring segment has no complete event capacity')
        counts = struct.unpack_from('<' + 'I' * total_units, data, base + 16)
        for selected_index, warp in enumerate(units):
            count_words = counts[warp]
            if count_words % 2:
                raise ValueError('Incomplete 64-bit entry count')
            written = count_words // 2
            retained = min(written, capacity)
            dropped = max(0, written - capacity)
            losses.append({'program': program, 'sm': sm, 'warp': warp, 'written_records': written,
                           'retained_records': retained, 'dropped_records': dropped, 'capacity_records': capacity})
            pending = {}
            occurrences = {}
            for position in range(retained):
                ordinal = dropped + position
                physical = ordinal % capacity
                offset = base + metadata_size + selected_index * segment_size + physical * 8
                tag, low = struct.unpack_from('<2I', data, offset)
                site = (tag >> 23) & 255
                tick = ((tag & 2047) << 32) | low
                end = bool(tag & 0x80000000)
                record = {'program': program, 'sm': sm, 'warp': warp, 'site': site,
                          'record_ordinal': ordinal, 'tick': tick, 'phase': 'exit' if end else 'entry'}
                records.append(record)
                if not end:
                    if site in pending:
                        unpaired.append({**pending[site], 'reason': 'entry_overwrites_pending_entry'})
                    pending[site] = record
                    continue
                start = pending.pop(site, None)
                if start is None:
                    unpaired.append({**record, 'reason': 'exit_without_retained_entry'})
                    continue
                if tick < start['tick']:
                    unpaired.extend([{**start, 'reason': 'clock_wrap_not_verified'}, {**record, 'reason': 'clock_wrap_not_verified'}])
                    continue
                occurrence = occurrences.get(site, 0)
                occurrences[site] = occurrence + 1
                clock = {'domain': 'nvidia.SM.clock', 'scope': f'SM:{sm}', 'alignment': 'instance_local',
                         'tick_ns': None, 'wrap_bits': clock_bits, 'origin_tick': None,
                         'encoding': 'clock_low32' if clock_bits == 32 else 'low_43_bits_of_clock64'}
                associated = invocation_id is not None and bool(association_evidence)
                observations.append({'id': f'{capture_id}:p{program}:w{warp}:r{start["record_ordinal"]}',
                                     'capture_id': capture_id, 'source': 'proton_nvidia_ring',
                                     'invocation_id': invocation_id,
                                     'association_status': 'verified' if associated else 'unassociated',
                                     'association_evidence': association_evidence,
                                     'semantic': 'source_control_interval', 'program': program,
                                     'actor': f'SM:{sm}/warp:{warp}', 'site': site, 'scope_name': scope_names.get(site),
                                     'occurrence': occurrence if not dropped else None,
                                     'retained_occurrence': occurrence,
                                     'record_ordinal': start['record_ordinal'], 'iteration': None, 'buffer_slot': None,
                                     'start_tick': start['tick'], 'end_tick': tick, 'clock': clock,
                                     'unit': 'cycles', 'granularity': 'warp',
                                     'collection_site': 'explicit_proton_scope_boundaries',
                                     'sampling': {'selected_warps': list(units), 'total_warps': total_units},
                                     'truncated': bool(dropped),
                                     'duration_ticks': tick - start['tick'], 'duration_ns': None})
            unpaired.extend({**record, 'reason': 'entry_without_retained_exit'} for record in pending.values())
    return {'schema_version': 1, 'backend': 'cuda', 'capture_id': capture_id,
            'observations': observations, 'records': records, 'losses': losses,
            'unpaired_records': unpaired, 'dropped_records': sum(item['dropped_records'] for item in losses),
            'clock_relation': 'unverified_to_cupti',
            'limitations': ['Recorded scope IDs are eight bits; unsupported wider identities are rejected.',
                            'Cycles remain SM-local raw ticks; no static-clock or interval scaling converts to ns.',
                            'Source-control intervals do not establish asynchronous completion or engine busy time.',
                            'Occurrence counts are per retained site/actor; source iteration variables are unknown.',
                            'Dynamic identity requires caller-supplied verified invocation association evidence.']}


def lower_request(request):
    """Lower supported semantics to inherited GPU recording and explicit output selection.

    Program selection is lowered to physical linear CTA predicates for
    num_ctas=1. Site selection remains a postcapture output filter.
    """
    value = request.as_dict() if hasattr(request, 'as_dict') else dict(request)
    if value.get('semantics', ['source_control_interval']) != ['source_control_interval']:
        raise ValueError('NVIDIA Proton supports only explicit source_control_interval observations')
    if value.get('sample_every', 1) != 1:
        raise ValueError('NVIDIA Proton has no device occurrence sampling; sample_every must be 1')
    count = value.get('max_events_per_instance', 256)
    if type(count) is not int or count < 1:
        raise ValueError('max_events_per_instance must be a positive integer')
    for field in ('programs', 'sites'):
        selected = value.get(field, [0] if field == 'programs' else None)
        if selected is not None and (not isinstance(selected, (list, tuple)) or not selected
                                     or any(type(item) is not int or item < 0 for item in selected)
                                     or len(set(selected)) != len(selected)):
            raise ValueError(f'{field} must be a unique nonnegative identity list or null')
        if field == 'sites' and selected is not None and any(item > 255 for item in selected):
            raise ValueError('NVIDIA Proton scope identity is limited to eight bits')
        value[field] = None if selected is None else list(selected)
    value.setdefault('semantics', ['source_control_interval'])
    value.setdefault('sample_every', 1)
    value['max_events_per_instance'] = count
    return {'backend': 'cuda', 'status': 'supported_with_device_program_selection',
            'mode_options': {'sampling_strategy': 'selective', 'sampling_options': '0',
                             'granularity': 'warp', 'buffer_size': count * 2 * 8},
            'collection_scope': {'programs': value['programs'] if value['programs'] is not None else 'all_launched_CTAs', 'warps': [0],
                                 'sites': 'all_explicit_proton_scopes',
                                 'capacity_primitive_records_per_program_warp': count * 2},
            'output_selection': value,
            'requirements': ['Explicit Proton scope annotations are required.',
                             'Triton semantics require explicit opt-in to the verified non-pipelined subset.'],
            'limitations': ['Program IDs select physical linear CTAs on device with num_ctas=1; site selection filters output after collection.',
                            'Warp selection and ring capacity are the inherited device-side controls.',
                            'No verified conversion to nanoseconds or alignment to CUPTI is supplied.']}


def select_observations(decoded, plan):
    """Apply declared output filtering, retaining collection loss separately."""
    selection = plan['output_selection']
    programs, sites = selection['programs'], selection['sites']
    counts = {}
    result = []
    filtered, capped = 0, 0
    for event in decoded['observations']:
        if ((programs is not None and event['program'] not in programs)
                or (sites is not None and event['site'] not in sites)):
            filtered += 1
            continue
        key = event['program']
        if counts.get(key, 0) >= selection['max_events_per_instance']:
            capped += 1
            continue
        counts[key] = counts.get(key, 0) + 1
        result.append(event)
    return {**decoded, 'observations': result, 'collection_scope': plan['collection_scope'],
            'output_selection': selection, 'selection_stage': 'device_program_and_postcapture_site' if programs is not None else 'postcapture',
            'output_filtered_intervals': filtered, 'output_capacity_excluded_intervals': capped}
