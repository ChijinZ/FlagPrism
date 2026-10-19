"""Collective shared-byte lifecycles over actual late NVPTX observations.

This is not a physical recording ABI, machine-placement proof or time-flow grant.
The model consumes all actors of a uniform CTA path. It preserves native absolute
shared addresses; each program supplies its actual dynamic-shared symbol base.
"""
from collections import Counter
import hashlib
import struct


class LateModelError(ValueError):
    pass


def _need(value, message):
    if not value:
        raise LateModelError(message)


def decode_probe(manifest, metadata, allocation):
    """Decode original words, never cached event/status fields."""
    _need(
        type(allocation) is bytes and len(allocation) % 8 == 0,
        'Invalid original allocation bytes')
    actors, capacity = manifest['actors'], manifest['capacity_per_program']
    header, stride = manifest['header_words'], manifest['segment_words']
    _need(
        type(actors) is int and actors == 128 and type(capacity) is int
        and 1 <= capacity <= 4096 and type(header) is int and header == 6,
        'Unsupported bounded experimental layout')
    _need(
        type(stride) is int and stride == actors * (header + 4 * capacity)
        and metadata['stride_words'] == stride
        and metadata['word_count'] == len(allocation) // 8,
        'Manifest/allocation dimensions differ')
    guard = metadata['guard_words']
    _need(
        type(guard) is int and 1 <= guard <= 1024,
        'Invalid allocation guard size')
    words = struct.unpack('<' + str(len(allocation) // 8) + 'Q', allocation)
    _need(words[:guard] == words[-guard:] == (0x5A5A1234, ) * guard,
          'Original allocation guard changed')
    words = words[guard:-guard]
    _need(
        len(words) % stride == 0 and 1 <= len(words) // stride <= 4096,
        'Incomplete program allocation')
    sites = {}
    for row in manifest['sites']:
        site = row['site_id']
        _need(
            type(site) is int and site > 0 and site not in sites,
            'Duplicate or invalid site')
        _need(
            row['kind'] in {
                'copy_submit_after', 'commit_after', 'wait_bracket',
                'cta_barrier_after', 'shared_store_after',
                'shared_load_issue_bracket', 'shared_load_native_bracket',
                'matrix_issue_bracket', 'warp_sync_issue_bracket'
            }, 'Unknown native observation kind')
        if row['kind'] == 'shared_load_issue_bracket' and 'members' in row:
            allowed = {
                'llvm.nvvm.ldmatrix.sync.aligned.m8n8.x4.b16.p3',
                'llvm.nvvm.ldmatrix.sync.aligned.m8n8.x4.trans.b16.p3'
            }
            _need(
                type(row['members']) is list and row['members'] and all(
                    m.get('native_operation') in allowed
                    for m in row['members']),
                'Unmodeled native ldmatrix operand geometry')
        sites[site] = row
    count_programs = len(words) // stride
    expected_programs = list(range(count_programs))
    if manifest.get('compact_programs'):
        grid = metadata['grid']
        _need(
            type(grid) is list and len(grid) == 3
            and all(type(v) is int and v > 0 for v in grid),
            'Missing actual launch grid for compact sampling')
        total = grid[0] * grid[1] * grid[2]
        expected_programs = [0] if total == 1 else [0, total - 1]
        _need(count_programs == len(expected_programs),
              'Physical allocation differs from selected logical programs')
    result = []
    for program in range(len(words) // stride):
        part = words[program * stride:(program + 1) * stride]
        sequences, shared_bases = [], set()
        for actor in range(actors):
            count, overflow, magic, identity, base, actual_actor = [
                part[i * actors + actor] for i in range(header)
            ]
            _need(
                0 < count <= capacity and overflow == 0 and magic == 0x46504C34
                and identity == expected_programs[program]
                and actual_actor == actor,
                'Incomplete/mixed actor publication')
            shared_bases.add(base)
            rows, previous = [], 0
            for occurrence in range(count):
                site, begin, end, payload = [
                    part[(header + 4 * occurrence + i) * actors + actor]
                    for i in range(4)
                ]
                _need(site in sites and previous <= begin <= end and begin > 0,
                      'Invalid site or observer clock order')
                previous = end
                rows.append(
                    dict(site_id=site,
                         begin_tick=begin,
                         end_tick=end,
                         payload=payload))
            _need(
                all(part[i * actors + actor] == 0
                    for i in range(header + 4 * count, header + 4 * capacity)),
                'Unpublished actor record words')
            sequences.append(rows)
        _need(len(shared_bases) == 1, 'Actors disagree on actual shared base')
        _need(
            all([r['site_id']
                 for r in rows] == [r['site_id'] for r in sequences[0]]
                for rows in sequences),
            'Divergent actor paths need a richer dynamic participation model')
        result.append(
            dict(program=expected_programs[program],
                 physical_slot=program,
                 shared_base=shared_bases.pop(),
                 actors=sequences))
    return dict(programs=result,
                sites=sites,
                shared_bytes=metadata['shared_bytes'],
                raw_sha256=hashlib.sha256(allocation).hexdigest())


def _ranges(footprint, base):
    """Compact exact physical bytes as offset/length pairs, without gap filling."""
    result = []
    for byte in sorted(footprint):
        offset = byte - base
        if result and result[-1][0] + result[-1][1] == offset:
            result[-1][1] += 1
        else:
            result.append([offset, 1])
    return result


def analyze_probe(decoded):
    """Check byte producers, local commit/wait order and CTA publication cuts.

    Completion here means observed by a native wait, not the unknown physical
    completion instant. CTA barrier cuts justify cross-actor shared visibility;
    clocks are not compared across actors. No hardware activity span is inferred.
    """
    reports = []
    for program in decoded['programs']:
        base, size = program['shared_base'], decoded['shared_bytes']
        _need(
            type(size) is int and 0 < size <= 1 << 20,
            'Invalid actual shared allocation length')
        actors = program['actors']
        memory, generations, committed, pending = {}, {}, [], None
        edges, reuse = [], []
        last_barrier, barriers = -1, 0

        def new_generation(identity, kind):
            _need(identity not in generations, 'Repeated generation identity')
            item = dict(identity=identity,
                        kind=kind,
                        completed=False,
                        visible=False,
                        bytes=set(),
                        submit_sequences=[],
                        submissions=[],
                        commit_sequence=None,
                        completion_observed_sequence=None,
                        completion_observation_kind=None,
                        publication_barrier_sequence=None,
                        consumer_sequences=[],
                        last_read=-1)
            generations[identity] = item
            return item

        def write(footprint, generation, sequence):
            prior = Counter(memory[b] for b in footprint if b in memory)
            for identity in sorted(prior):
                old = generations[identity]
                if old is generation:
                    continue
                _need(
                    old['completed'],
                    'Shared bytes overwritten before prior producer completion'
                )
                _need(old['last_read'] < last_barrier or old['last_read'] < 0,
                      'Shared bytes reused without a CTA cut after consumers')
                reuse.append(
                    dict(
                        previous=identity,
                        next=generation['identity'],
                        sequence=sequence,
                        overlapping_bytes=prior[identity],
                        overlapping_shared_ranges=_ranges(
                            {
                                b
                                for b in footprint if memory.get(b) == identity
                            }, base),
                        barrier_sequence=last_barrier))
            for byte in footprint:
                memory[byte] = generation['identity']
            generation['bytes'].update(footprint)
            generation['submit_sequences'].append(sequence)
            generation['submissions'].append(
                dict(sequence=sequence,
                     bytes=len(footprint),
                     shared_ranges=_ranges(footprint, base)))

        for sequence in range(len(actors[0])):
            first = actors[0][sequence]
            site = decoded['sites'][first['site_id']]
            kind = site['kind']
            rows = [a[sequence] for a in actors]
            if kind in ('copy_submit_after', 'shared_store_after',
                        'shared_load_issue_bracket',
                        'shared_load_native_bracket'):
                footprint = set()
                for row in rows:
                    payload = row['payload']
                    if kind == 'shared_load_issue_bracket':
                        address, width = payload, 16
                    else:
                        address, high = payload & 0xFFFFFFFF, payload >> 32
                        if kind == 'copy_submit_after':
                            width = site['destination_bytes']
                            _need(
                                width == 16 and 0 <= high <= width,
                                'Invalid native copy source-valid byte count')
                        else:
                            width = high
                            _need(
                                width == site['destination_bytes']
                                and 0 < width <= 256,
                                'Native shared access width differs')
                    _need(base <= address and address + width <= base + size,
                          'Native footprint outside actual shared allocation')
                    footprint.update(range(address, address + width))
                if kind == 'copy_submit_after':
                    if pending is None:
                        pending = new_generation(
                            'async-' + str(len(committed) + 1), 'async')
                    write(footprint, pending, sequence)
                elif kind == 'shared_store_after':
                    generation = new_generation('sync-' + str(sequence),
                                                'sync')
                    # Shared issue is ordered, cross-actor publication still
                    # requires the native CTA barrier recorded below.
                    write(footprint, generation, sequence)
                else:
                    _need(all(b in memory for b in footprint),
                          'Shared consumer byte has no observed producer')
                    sources = Counter(memory[b] for b in footprint)
                    for identity, count in sorted(sources.items()):
                        generation = generations[identity]
                        _need(
                            generation['completed'] and generation['visible'],
                            'Consumer precedes native completion/publication')
                        generation['last_read'] = sequence
                        generation['consumer_sequences'].append(sequence)
                        edges.append(
                            dict(producer=identity,
                                 consumer_sequence=sequence,
                                 consumer_site=site['site_id'],
                                 consumer_kind=kind,
                                 bytes=count,
                                 shared_ranges=_ranges(
                                     {
                                         b
                                         for b in footprint
                                         if memory[b] == identity
                                     }, base),
                                 publication_barrier=generation[
                                     'publication_barrier_sequence']))
            elif kind == 'commit_after':
                if pending is None:
                    pending = new_generation(
                        'async-' + str(len(committed) + 1), 'async')
                pending['commit_sequence'] = sequence
                committed.append(pending['identity'])
                pending = None
            elif kind == 'wait_bracket':
                values = {r['payload'] for r in rows}
                _need(
                    len(values) == 1 and 0 <= next(iter(values)) <= 7,
                    'Invalid or mixed native wait operand')
                limit = next(iter(values))
                for identity in committed[:max(0, len(committed) - limit)]:
                    generation = generations[identity]
                    if not generation['completed']:
                        generation['completion_observed_sequence'] = sequence
                        generation[
                            'completion_observation_kind'] = 'native_wait_return'
                    generation['completed'] = True
            elif kind == 'cta_barrier_after' or (
                    kind == 'warp_sync_issue_bracket' and len(actors) <= 32
                    and {r['payload']
                         for r in rows} == {0xffffffff}):
                if kind == 'cta_barrier_after':
                    _need({r['payload']
                           for r in rows} == {0},
                          'Only actual all-CTA barrier zero is modeled')
                last_barrier, barriers = sequence, barriers + 1
                for generation in generations.values():
                    if generation[
                            'kind'] == 'sync' and not generation['completed']:
                        generation['completed'] = True
                        generation['completion_observed_sequence'] = sequence
                        generation['completion_observation_kind'] = (
                            'native_cta_barrier_return'
                            if kind == 'cta_barrier_after' else
                            'full_block_warp_barrier_return_observed')
                    if generation['completed'] and not generation['visible']:
                        generation['visible'] = True
                        generation['publication_barrier_sequence'] = sequence
            # A partial/multi-warp synchronization remains an observation;
            # it cannot publish shared bytes for the entire CTA. The full-block
            # case above additionally requires a native-bound mask in the
            # dependency provider before it can qualify any time arrows.
            elif kind not in ('warp_sync_issue_bracket',
                              'matrix_issue_bracket', 'compute_issue_bracket',
                              'global_load_issue_bracket',
                              'global_store_issue_bracket',
                              'global_atomic_issue_bracket'):
                raise LateModelError('Unhandled native observation')
        _need(
            pending is None
            and all(generations[g]['completed'] for g in committed),
            'Final async producer groups were not drained')
        reports.append(
            dict(program=program['program'],
                 shared_base=base,
                 shared_bytes=size,
                 commit_groups=len(committed),
                 barriers=barriers,
                 generations=[
                     dict(identity=g['identity'],
                          kind=g['kind'],
                          footprint_bytes=len(g['bytes']),
                          shared_ranges=_ranges(g['bytes'], base),
                          submit_sequences=g['submit_sequences'],
                          submissions=g['submissions'],
                          commit_sequence=g['commit_sequence'],
                          completion_observed_sequence=g[
                              'completion_observed_sequence'],
                          completion_observation_kind=g[
                              'completion_observation_kind'],
                          publication_barrier_sequence=g[
                              'publication_barrier_sequence'],
                          consumer_sequences=g['consumer_sequences'])
                     for g in generations.values()
                 ],
                 consumer_edges=edges,
                 reuse=reuse))
    return dict(
        model='nvidia.late.shared_byte_lifecycle.v2',
        shared_range_encoding='offset_from_actual_shared_base,length_bytes',
        status='prototype_dynamic_byte_model_consistent',
        raw_sha256=decoded['raw_sha256'],
        programs=reports,
        machine_site_binding_verified=False,
        clock_comparison_qualified=False,
        time_flows_qualified=False,
        source_cost_qualified=False,
        hardware_busy_qualified=False)
