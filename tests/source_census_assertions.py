"""Independent raw-byte oracle for the public default automatic drivers.

Counts are source-control visits of the declared observer, including all-false
masks. A normalized row is one nonzero cell, never one dynamic occurrence.
No product census decoder participates in these assertions.
"""
import base64
import hashlib
import json
import math
import struct
from collections import Counter

from flagtree.profiler.export_refs import restore


def read_view(bundle, name, observations):
    return restore(json.loads((bundle / 'ai' / name).read_text()),
                   observations)


def validate_document(document, backend):
    """Check every physical byte, then the exact selected-program row set."""
    all_cells = []
    summaries = []
    capture_ids = [c['capture_id'] for c in document['captures']]
    assert len(set(capture_ids)) == len(capture_ids)
    assert set(r['capture_id']
               for r in document['observations']) <= set(capture_ids)
    for capture in document['captures']:
        raw = base64.b64decode(capture['raw_base64'], validate=True)
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == capture['raw_sha256']
        if backend == 'nvidia':
            assert capture['raw_encoding'] == 'base64_source_census_v1'
            descriptors = [capture['census']]
            summary, loss = capture['decoded']['summary'], capture['decoded'][
                'loss']
            binary, invocation = capture['binary_id'], capture['invocation_id']
            expected_bytes = descriptors[0]['program_count'] * descriptors[0][
                'program_stride']
            used = set()
        else:
            assert capture['capture_status'] == 'decoded'
            assert capture['decode_error'] is None
            assert not capture['counter_saturated']
            metadata = capture['runtime_metadata']
            proof = metadata['profiler_association_evidence']
            binary, invocation = proof['binary_id'], proof['invocation_id']
            assert invocation == metadata['profiler_invocation_id']
            if backend == 'enflame':
                assert capture['raw_encoding'] == 'base64_source_census_v1'
                census = capture['source_census']
                descriptors = [census['descriptor']]
                d = descriptors[0]
                expected_bytes = 32 + d['program_count'] * d['program_stride']
                assert struct.unpack_from(
                    '<8I', raw) == (0, d['program_count'] * len(d['sites']), 0,
                                    0, 64, expected_bytes, 0, 0)
            else:
                census = metadata['ascend_source_census']
                descriptors = census['descriptors']
                physical = census['physical_plan']
                assert physical['version'] in (1, 2)
                assert physical['program_count'] == math.prod(physical['grid'])
                assert physical['actor_slots'] == 3 and physical[
                    'site_stride'] == 8
                assert physical[
                    'actor_stride'] == physical['reserved_sites'] * 8
                assert physical[
                    'program_stride'] == 3 * physical['actor_stride']
                expected_bytes = 32 + physical['program_count'] * physical[
                    'program_stride']
                assert physical['byte_count'] == expected_bytes
                assert physical[
                    'reserved_cell_count'] * 8 == expected_bytes - 32
                assert not any(raw[:32])
                assert capture[
                    'raw_encoding'] == 'base64_' + physical['layout']
            summary, loss = census['summary'], census['loss']
            used = set(range(32))
        assert binary and invocation and len(raw) == expected_bytes
        assert loss['exact'] is True and loss['overflow_cells'] == 0
        assert loss['sampling'] is False and loss[
            'capture_policy'] == 'all_grid_census'
        cells = {}
        for d in descriptors:
            assert d['schema'] == 'flagprism.source-census' and d[
                'version'] == 1
            assert d['cell_size'] == 8 and d['byte_order'] == 'little'
            assert d['program_count'] == math.prod(d['grid'])
            assert d['raw_sha256'] == digest
            if backend in ('nvidia', 'ascend'):
                assert (d['binary_id'], d['invocation_id']) == (binary,
                                                                invocation)
            if backend == 'nvidia':
                assert d['compiler_ir_sha256'] == capture['compiler_ir_sha256']
            assert len({s['site'] for s in d['sites']}) == len(d['sites'])
            assert len({(a['kind'], a['id'])
                        for a in d['actors']}) == len(d['actors'])
            for program in range(d['program_count']):
                for ai, actor in enumerate(d['actors']):
                    for si, site in enumerate(d['sites']):
                        offset = (d['cells_offset'] +
                                  program * d['program_stride'] +
                                  ai * d['actor_stride'] +
                                  si * d['site_stride'])
                        assert 0 <= offset <= len(raw) - 8
                        assert not used.intersection(range(offset, offset + 8))
                        used.update(range(offset, offset + 8))
                        count, flags = struct.unpack_from('<II', raw, offset)
                        assert flags in (0, 1) and bool(flags) == bool(count)
                        assert site['role'] in ('primary', 'context')
                        cells[offset] = dict(capture_id=capture['capture_id'],
                                             program=program,
                                             actor=actor,
                                             site=site['site'],
                                             site_role=site['role'],
                                             count=count,
                                             raw_offset=offset,
                                             compiler_site=site)
        # GCU reserves 64 bytes per site; Ascend includes unused actor columns.
        assert all(value == 0 for i, value in enumerate(raw) if i not in used)
        primary = {
            c['program']
            for c in cells.values()
            if c['count'] and c['site_role'] == 'primary'
        }
        selected = min(primary) if primary else None
        assert summary['selected_program'] == selected
        assert summary['selection_is_presentation_only'] is True
        expected = {
            off: c
            for off, c in cells.items()
            if c['program'] == selected and c['count']
        }
        rows = [
            r for r in document['observations']
            if r['capture_id'] == capture['capture_id']
        ]
        assert len(rows) == len(expected)
        assert {r['raw_offset'] for r in rows} == set(expected)
        for row in rows:
            cell = expected[row['raw_offset']]
            for key in ('program', 'site', 'site_role', 'count'):
                assert row[key] == cell[key], (key, row, cell)
            assert (row['actor']['kind'],
                    row['actor']['id']) == (cell['actor']['kind'],
                                            cell['actor']['id'])
            assert row['semantic'] == 'counter' and row['count_exact'] is True
            assert row['value'] == row['count'] and row['overflow'] is False
            assert row['raw_sha256'] == digest
            assert (row['binary_id'], row['invocation_id']) == (binary,
                                                                invocation)
            assert row['association_status'] == 'verified'
            assert all(
                row.get(k) is None
                for k in ('occurrence', 'iteration', 'clock', 'start_tick',
                          'end_tick', 'duration_ticks', 'duration_ns',
                          'relative_start_ns'))
            site = row['compiler_site']
            assert site['site'] == row['site']
            assert site['binary_id'] == binary and site['scope_id'] == row[
                'site']
            assert site['kind'] == 'automatic_compiler_operation'
            assert site['origin'] == cell['compiler_site']['origin']
            assert site.get('operation', site['origin'].get('operation'))
            origin = site['origin']
            assert origin.get('source_locations') or origin.get(
                'source_capture')
        all_cells.extend(cells.values())
        summaries.append(
            dict(capture_id=capture['capture_id'],
                 selected_program=selected,
                 active_programs=sorted(primary),
                 physical_cells=len(cells),
                 raw_bytes=len(raw),
                 normalized_rows=len(rows),
                 exact=True))
    return all_cells, summaries


def validate_bundle(bundle, backend):
    document = json.loads((bundle / 'ai/observations.json').read_text())
    assert document['captures']
    cells, summaries = validate_document(document, backend)
    fine = read_view(bundle, 'fine_grained.json', document)
    records = document['observations']
    assert len(fine['records']) == len(records)
    assert Counter((r['capture_id'], r['raw_offset'], r['count'])
                   for r in records) == Counter(
                       (r['capture_id'], r['raw_offset'], r['count'])
                       for r in fine['records'])
    by_offset = {(r['capture_id'], r['raw_offset']): r for r in records}
    for row in fine['records']:
        original = by_offset[(row['capture_id'], row['raw_offset'])]
        for key in ('program', 'site', 'site_role', 'binary_id',
                    'invocation_id', 'semantic', 'count_exact', 'overflow',
                    'raw_sha256'):
            assert row[key] == original[key]
        site = original['compiler_site']
        assert row['operation'] == site.get('operation',
                                            site['origin'].get('operation'))
    assert all(r['source_locations'] and r['operation']
               and r['association_status'] == 'verified'
               for r in fine['records'])
    assert (bundle / 'report/fine_grained.html').is_file()
    read_view(bundle, 'observation_plan.json', document)
    return document, cells, summaries, fine
