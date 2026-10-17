"""NVIDIA timeline-v2 physical decoder; no clock or dependency certification.

Input is invocation-owned device scratch *after* its actual writers complete.
A slot map binds compact or full-grid allocation slots to real logical programs.
This module never derives nanoseconds, source costs, epochs, or hardware flows.
"""
from __future__ import annotations

import struct

RECORD_VERSION = 2
RECORD_BYTES = 16
PREAMBLE = 0x46505432
SATURATED = 0xFFFFFFFF


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def decode_timeline_ring(payload, *, scratch_size, total_warps,
                         selected_warps, slots, scope_ids, record_version=2):
    """Decode actual records while retaining absolute sequences and all offsets.

    ``slots`` consists of (physical allocation slot, expected logical program).
    Ring overwrite and saturated counters remain incomplete, even if some
    retained begin/end records happen to form pairs. Callers must validate the
    manifest/capture identity and clock evidence separately before exporting.
    """
    if type(record_version) is not int or record_version != RECORD_VERSION:
        raise ValueError('Unsupported NVIDIA timeline record version')
    if not isinstance(payload, bytes):
        raise ValueError('Timeline payload must be immutable bytes')
    _integer(scratch_size, 'scratch_size', 1)
    _integer(total_warps, 'total_warps', 1)
    metadata_size = 16 + total_warps * 4
    if metadata_size >= scratch_size or len(payload) % scratch_size:
        raise ValueError('Truncated payload or impossible scratch metadata')
    if not isinstance(selected_warps, tuple) or not selected_warps:
        raise ValueError('selected_warps must be a nonempty tuple')
    for warp in selected_warps:
        _integer(warp, 'selected warp')
        if warp >= total_warps:
            raise ValueError('Selected warp is outside the compiled topology')
    if tuple(sorted(set(selected_warps))) != selected_warps:
        raise ValueError('Selected warps must be unique and ordered')
    if not isinstance(scope_ids, frozenset) or not scope_ids:
        raise ValueError('scope_ids must be a nonempty frozen manifest set')
    for site in scope_ids:
        _integer(site, 'scope id')
        if site > 0x7FFFFFFF:
            raise ValueError('Scope id exceeds the timeline tag field')
    if not isinstance(slots, tuple) or not slots:
        raise ValueError('slots must be a nonempty tuple')
    seen_slots, seen_programs = set(), set()
    for entry in slots:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError('Slot map entries must be (slot, program) tuples')
        slot, program = entry
        _integer(slot, 'allocation slot')
        _integer(program, 'logical program')
        if slot >= len(payload) // scratch_size or program > 0xFFFFFFFF:
            raise ValueError('Slot or program exceeds the declared encoding')
        if slot in seen_slots or program in seen_programs:
            raise ValueError('Slot map aliases an invocation program')
        seen_slots.add(slot)
        seen_programs.add(program)

    records, observers = [], []
    for slot, expected_program in slots:
        base = slot * scratch_size
        magic, program, sm, buffer_size = struct.unpack_from('<4I', payload, base)
        if magic != PREAMBLE or program != expected_program:
            raise ValueError('Missing timeline-v2 header or wrong logical program')
        if (buffer_size == 0 or buffer_size + metadata_size > scratch_size or
                buffer_size % (len(selected_warps) * RECORD_BYTES)):
            raise ValueError('Invalid timeline ring extent or entry alignment')
        segment_bytes = buffer_size // len(selected_warps)
        if segment_bytes & (segment_bytes - 1):
            raise ValueError('Compiled timeline segment must be a power of two')
        capacity = segment_bytes // RECORD_BYTES
        for segment, warp in enumerate(selected_warps):
            count_offset = base + 16 + warp * 4
            count_words, = struct.unpack_from('<I', payload, count_offset)
            saturated = count_words == SATURATED
            if not saturated and count_words % 4:
                raise ValueError('Timeline counter contains a partial record')
            # The producer freezes before its aligned word counter wraps. The
            # sentinel represents one or more rejected subsequent attempts.
            written = (SATURATED - 3 if saturated else count_words) // 4
            retained = min(written, capacity)
            overwritten = max(written - capacity, 0)
            observers.append({
                'slot': slot, 'program': program, 'warp': warp, 'sm': sm,
                'counter_byte_offset': count_offset,
                'counter_byte_length': 4, 'counter_words': count_words,
                'capacity_records': capacity, 'written_records': written,
                'retained_records': retained, 'overwritten_records': overwritten,
                'saturated': saturated,
                'unrecorded_after_saturation': None if saturated else 0,
                'complete': not saturated and overwritten == 0,
            })
            previous_tick = None
            for ordinal in range(written - retained, written):
                offset = (base + metadata_size + segment * segment_bytes +
                          (ordinal % capacity) * RECORD_BYTES)
                tag, low, high, sequence = struct.unpack_from('<4I', payload, offset)
                if sequence != ordinal:
                    raise ValueError('Record sequence disagrees with its ring position')
                site = tag & 0x7FFFFFFF
                if site not in scope_ids:
                    raise ValueError('Record site is absent from this binary manifest')
                tick = (high << 32) | low
                if previous_tick is not None and tick < previous_tick:
                    raise ValueError('Timeline timer regressed; epoch/wrap not established')
                previous_tick = tick
                records.append({
                    'slot': slot, 'program': program, 'warp': warp, 'sm': sm,
                    'site': site, 'sequence': sequence, 'tick': tick,
                    'phase': 'exit' if tag & 0x80000000 else 'entry',
                    'raw_byte_offset': offset, 'raw_byte_length': RECORD_BYTES,
                    'counter_byte_offset': count_offset,
                })
    return {'record_version': RECORD_VERSION, 'record_bytes': RECORD_BYTES,
            'timer_bits': 64, 'records': records, 'observers': observers,
            'complete': all(row['complete'] for row in observers)}
