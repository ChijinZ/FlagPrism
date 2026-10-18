"""Decode bounded late-recorder bytes without assuming collective execution.

This raw layer accepts arrived-empty and divergent observer streams. It grants
no shared-memory dependency, machine-boundary, clock-unit or epoch proof.
Dependency analysis is a separate consumer with its own eligibility checks.
"""
import hashlib
import struct


class LateRawError(ValueError):
    pass


def _int(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise LateRawError('Invalid ' + label)
    return value


def decode_late_raw(manifest, raw, *, slots):
    """Decode exact header/record spans in program/logical-word/actor order.

    ``slots`` is the binary-bound allocator's physical-slot/logical-program map,
    never inferred from potentially corrupt records. ``raw`` excludes separately
    retained allocator guards; their integrity is checked by the runtime owner.
    """
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise LateRawError('Unknown late manifest schema')
    if (manifest.get('word_layout') != 'program/logical_word/actor'
            or manifest.get('profile_argument_abi') != 1):
        raise LateRawError('Unknown late recording layout/argument ABI')
    actors = _int(manifest.get('actors'), 'actor count', 1, 1024)
    capacity = _int(manifest.get('capacity_per_program'), 'capacity', 1, 4096)
    if manifest.get('header_words') != 6:
        raise LateRawError('Unknown late record header')
    stride = actors * (6 + 4 * capacity)
    if manifest.get('segment_words') != stride:
        raise LateRawError('Manifest stride differs from record layout')
    if type(raw) is not bytes or len(raw) > 8 * 1024 * 1024:
        raise LateRawError('Raw bytes exceed bounded capture budget')
    if type(slots) not in (tuple, list) or len(slots) > 2:
        raise LateRawError('Expected compact first/last slot mapping')
    normalized = []
    for index, pair in enumerate(slots):
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise LateRawError('Malformed binary-bound program slot')
        physical = _int(pair[0], 'physical slot', 0, 1)
        program = _int(pair[1], 'logical program', 0, 0xffffffff)
        if physical != index:
            raise LateRawError('Physical slots must be contiguous')
        normalized.append((physical, program))
    if len(set(p for _, p in normalized)) != len(normalized):
        raise LateRawError('Logical program identity reused')
    if normalized and (normalized[0][1] != 0 or
                       (len(normalized) == 2 and normalized[1][1] <= 0)):
        raise LateRawError('Compact runtime first/last identity differs')
    if len(raw) != stride * len(normalized) * 8:
        raise LateRawError('Raw byte length differs from admitted slots')
    inventory = manifest.get('sites')
    if type(inventory) is not list or not 1 <= len(inventory) <= 4096:
        raise LateRawError('Missing bounded site inventory')
    sites = {}
    for site in inventory:
        if type(site) is not dict:
            raise LateRawError('Malformed site inventory')
        key = _int(site.get('site_id'), 'site ID', 1, 4096)
        if key in sites or not isinstance(site.get('kind'), str):
            raise LateRawError('Duplicate or malformed site')
        semantics = site.get('record_semantics')
        if semantics not in ('observer_issue_bracket',
                             'observer_checkpoint_after'):
            raise LateRawError('Unknown site record semantics')
        sites[key] = site
    words = struct.unpack('<' + str(len(raw) // 8) + 'Q', raw)
    programs, complete = [], True
    for physical, program in normalized:
        observers = []
        for actor in range(actors):

            def word(row):
                return physical * stride + row * actors + actor

            header = [words[word(i)] for i in range(6)]
            count, overflow, magic, observed_program, shared_base, observed_actor = header
            if not magic:
                if any(words[word(row)] for row in range(6 + 4 * capacity)):
                    raise LateRawError(
                        'Unpublished observer contains records/header residue')
                observers.append(
                    dict(actor=actor,
                         arrived=False,
                         complete=False,
                         overflow=False,
                         events=[]))
                complete = False
                continue
            if (magic != 0x46504c34 or count > capacity
                    or overflow not in (0, 1) or observed_program != program
                    or observed_actor != actor):
                raise LateRawError(
                    'Observer identity/header differs from admitted layout')
            events, prior = [], None
            for occurrence in range(count):
                row = 6 + 4 * occurrence
                site_id, begin, end, payload = [
                    words[word(row + i)] for i in range(4)
                ]
                site = sites.get(site_id)
                if site is None or not 0 < begin <= end or (prior is not None
                                                            and begin < prior):
                    raise LateRawError(
                        'Invalid site or nonmonotonic observer ticks')
                if site['record_semantics'] == 'observer_checkpoint_after' and begin != end:
                    raise LateRawError(
                        'Checkpoint contains fabricated duration')
                events.append(
                    dict(site_id=site_id,
                         occurrence=occurrence,
                         kind=site['kind'],
                         begin_tick=begin,
                         end_tick=end,
                         payload=payload,
                         raw_begin_offset_bytes=word(row + 1) * 8,
                         raw_end_offset_bytes=word(row + 2) * 8,
                         raw_tag_offset_bytes=word(row) * 8,
                         raw_payload_offset_bytes=word(row + 3) * 8))
                prior = end
            if any(words[word(i)]
                   for i in range(6 + 4 * count, 6 + 4 * capacity)):
                raise LateRawError(
                    'Unpublished trailing record words are nonzero')
            observers.append(
                dict(actor=actor,
                     arrived=True,
                     complete=not bool(overflow),
                     overflow=bool(overflow),
                     shared_base=shared_base,
                     header_offset_bytes=word(0) * 8,
                     events=events))
            complete = complete and not bool(overflow)
        programs.append(
            dict(physical_slot=physical,
                 program_id=program,
                 observers=observers))
    return dict(schema_version=1,
                raw_sha256=hashlib.sha256(raw).hexdigest(),
                raw_bytes=len(raw),
                complete=complete,
                programs=programs,
                clock_comparison_qualified=False,
                source_cost_qualified=False,
                hardware_busy_qualified=False)
