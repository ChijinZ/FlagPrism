"""Transport-only CPU contracts; these fixtures do not prove a device producer."""
import struct

import pytest
from flagtree.profiler.ascend_census import (ACTOR_STRIDE, HEADER_BYTES,
                                             PROGRAM_STRIDE, actor_descriptor,
                                             plan_layout, validate_transport)


def test_physical_reserved_budget_and_actual_grid():
    plan = plan_layout([2, 3, 5])
    assert plan['program_count'] == 30
    assert plan['reserved_cell_count'] == 30 * 3 * 128
    assert plan['byte_count'] == 32 + 30 * 3072
    with pytest.raises(ValueError, match='cell budget'):
        plan_layout([2, 3, 5], max_cells=30 * 3 * 128 - 1)
    with pytest.raises(ValueError, match='byte budget'):
        plan_layout([2, 3, 5], max_bytes=plan['byte_count'] - 1)


def test_same_site_id_distinct_compiler_actors_share_one_raw():
    plan = plan_layout([2])
    raw = bytearray(plan['byte_count'])
    sites = [{'site': 7, 'role': 'primary'}]
    struct.pack_into('<II', raw, HEADER_BYTES + PROGRAM_STRIDE, 2, 1)
    struct.pack_into('<II', raw, HEADER_BYTES + PROGRAM_STRIDE + ACTOR_STRIDE,
                     5, 1)
    raw = bytes(raw)
    validate_transport(raw, plan, {0: sites, 1: sites})
    cube = actor_descriptor(raw,
                            plan,
                            slot=0,
                            sites=sites,
                            compiler_actor={
                                'kind': 'AIC',
                                'runtime_slot': 0
                            })
    vector = actor_descriptor(raw,
                              plan,
                              slot=1,
                              sites=sites,
                              compiler_actor={
                                  'kind': 'AIV',
                                  'runtime_slot': 1
                              })
    assert cube['cells_offset'] == HEADER_BYTES
    assert vector['cells_offset'] == HEADER_BYTES + ACTOR_STRIDE
    assert cube['raw_sha256'] == vector['raw_sha256']
    assert 'raw_base64' not in cube and 'raw_base64' not in vector


@pytest.mark.parametrize('offset',
                         [0, HEADER_BYTES + 8, HEADER_BYTES + ACTOR_STRIDE])
def test_reserved_header_site_or_actor_is_not_a_source_site(offset):
    plan = plan_layout([1])
    raw = bytearray(plan['byte_count'])
    struct.pack_into('<II', raw, offset, 1, 1)
    with pytest.raises(ValueError, match='header|padding'):
        validate_transport(bytes(raw), plan,
                           {0: [{
                               'site': 9,
                               'role': 'primary'
                           }]})


@pytest.mark.parametrize('count,flags,valid', [(0, 0, True), (2, 1, True),
                                               (0xffffffff, 1, True),
                                               (0xffffffff, 3, True),
                                               (2, 3, False), (0, 1, False),
                                               (3, 5, False)])
def test_saturation_and_flags(count, flags, valid):
    plan = plan_layout([1])
    raw = bytearray(plan['byte_count'])
    struct.pack_into('<II', raw, HEADER_BYTES, count, flags)
    if valid:
        validate_transport(bytes(raw), plan,
                           {0: [{
                               'site': 0,
                               'role': 'primary'
                           }]})
    else:
        with pytest.raises(ValueError, match='flags'):
            validate_transport(bytes(raw), plan,
                               {0: [{
                                   'site': 0,
                                   'role': 'primary'
                               }]})


def test_shared_actor_descriptors_have_unique_events_and_one_raw_reference():
    from flagtree.profiler.ascend_census import decode_shared_census
    plan = plan_layout([3])
    raw = bytearray(plan['byte_count'])
    sites = [{'site': 7, 'role': 'primary'}]
    struct.pack_into('<II', raw, HEADER_BYTES + PROGRAM_STRIDE, 2, 1)
    struct.pack_into('<II', raw, HEADER_BYTES + PROGRAM_STRIDE + ACTOR_STRIDE,
                     5, 1)
    result = decode_shared_census(bytes(raw),
                                  grid=[3],
                                  actors=[
                                      dict(slot=0,
                                           sites=sites,
                                           compiler_actor={
                                               'kind': 'AIC',
                                               'runtime_slot': 0
                                           }),
                                      dict(slot=1,
                                           sites=sites,
                                           compiler_actor={
                                               'kind': 'AIV',
                                               'runtime_slot': 1
                                           })
                                  ],
                                  capture_id='contract-fixture',
                                  invocation_id=None,
                                  binary_id='fixture')
    assert result['summary']['selected_program'] == 1
    events = result['observations']
    assert len({event['id'] for event in events}) == 2
    assert [event['count'] for event in events] == [2, 5]
    assert [event['actor']['id'] for event in events] == [0, 1]
    assert all(set(event['actor']) == {'kind', 'id'} for event in events)
    assert [
        event['compiler_site']['compiler_actor']['kind'] for event in events
    ] == ['AIC', 'AIV']
    assert all(event['clock'] is None and event['start_tick'] is None
               for event in events)
    assert all(event['association_status'] == 'unassociated'
               for event in events)
    assert all('raw_base64' not in descriptor
               for descriptor in result['descriptors'])
    assert all(descriptor['raw_ref']['capture_id'] == 'contract-fixture'
               for descriptor in result['descriptors'])
    assert all(descriptor['max_census_cells'] == 1048576
               and descriptor['max_census_bytes'] == 8388608
               for descriptor in result['descriptors'])


def test_zero_grid_has_no_actor_cells_or_synthetic_events():
    from flagtree.profiler.ascend_census import decode_shared_census
    result = decode_shared_census(bytes(HEADER_BYTES),
                                  grid=[0, 2, 3],
                                  actors=[
                                      dict(slot=2,
                                           sites=[{
                                               'site': 1,
                                               'role': 'primary'
                                           }],
                                           compiler_actor={
                                               'kind': 'AIV',
                                               'runtime_slot': 2
                                           })
                                  ],
                                  capture_id='empty-grid',
                                  invocation_id=None,
                                  binary_id='fixture')
    assert result['observations'] == []
    assert result['summary']['selected_program'] is None
    assert result['summary']['program_count'] == 0
    assert result['summary']['physical_byte_count'] == HEADER_BYTES


def test_sparse_actual_actor_columns_do_not_create_missing_sites():
    from flagtree.profiler.ascend_census import decode_shared_census
    plan = plan_layout([2])
    raw = bytearray(plan['byte_count'])
    struct.pack_into('<II', raw, 32 + 3072 + 1024 + 5 * 8, 7, 1)
    actor = dict(slot=1,
                 sites=[dict(site=77, role='primary', column=5)],
                 compiler_actor=dict(kind='AIV', runtime_slot=1))
    decoded = decode_shared_census(bytes(raw),
                                   grid=[2],
                                   actors=[actor],
                                   capture_id='sparse',
                                   invocation_id=None,
                                   binary_id='actual-compiler-binary')
    assert decoded['summary']['selected_program'] == 1
    assert len(decoded['observations']) == 1
    assert decoded['observations'][0]['site'] == 77
    assert decoded['descriptors'][0]['cells_offset'] == 32 + 1024 + 5 * 8
    assert [site['site']
            for site in decoded['descriptors'][0]['sites']] == [77]


@pytest.mark.parametrize('columns', [1, 8, 14, 18, 128])
def test_compact_physical_layout_uses_compiler_columns(columns):
    plan = plan_layout([257, 2, 3], version=2, site_count=columns)
    assert plan['layout'] == 'ascend_source_census_v2'
    assert plan['reserved_sites'] == columns
    assert plan['reserved_cell_count'] == 1542 * 3 * columns
    assert plan['byte_count'] == 32 + 1542 * 3 * columns * 8
    assert plan['actor_stride'] == columns * 8
    assert plan['program_stride'] == columns * 24
    with pytest.raises(ValueError, match='cell budget'):
        plan_layout([257, 2, 3],
                    version=2,
                    site_count=columns,
                    max_cells=plan['reserved_cell_count'] - 1)
    with pytest.raises(ValueError, match='byte budget'):
        plan_layout([257, 2, 3],
                    version=2,
                    site_count=columns,
                    max_bytes=plan['byte_count'] - 1)


@pytest.mark.parametrize('columns', [None, True, 0, 129, '8'])
def test_compact_layout_rejects_missing_or_invalid_compiler_columns(columns):
    with pytest.raises(ValueError, match='site_count'):
        plan_layout([1], version=2, site_count=columns)


def test_compaction_admits_large_grid_without_changing_either_budget():
    with pytest.raises(ValueError, match='cell budget'):
        plan_layout([4096])
    plan = plan_layout([4096], version=2, site_count=8)
    assert plan['byte_count'] == 786464
    assert plan['reserved_cell_count'] == 98304
    with pytest.raises(ValueError, match='128-column'):
        plan_layout([4096], version=1, site_count=8)


def test_compact_sparse_actor_offsets_and_unpresented_overflow():
    from flagtree.profiler.ascend_census import decode_shared_census
    plan = plan_layout([5], version=2, site_count=8)
    raw = bytearray(plan['byte_count'])
    first = 32 + plan['program_stride'] + plan['actor_stride'] + 6 * 8
    last = 32 + 4 * plan['program_stride'] + plan['actor_stride'] + 6 * 8
    struct.pack_into('<II', raw, first, 2, 1)
    struct.pack_into('<II', raw, last, 0xffffffff, 3)
    actor = dict(slot=1,
                 sites=[dict(site=77, role='primary', column=6)],
                 compiler_actor=dict(kind='AIV', runtime_slot=1))
    decoded = decode_shared_census(bytes(raw),
                                   grid=[5],
                                   actors=[actor],
                                   capture_id='compact',
                                   invocation_id=None,
                                   binary_id='fixture',
                                   version=2,
                                   site_count=8)
    assert decoded['storage'] == 'ascend_source_census_v2'
    assert decoded['summary']['selected_program'] == 1
    assert decoded['loss'][
        'overflow_cells'] == 1 and not decoded['loss']['exact']
    assert len(decoded['observations']) == 1
    assert decoded['observations'][0]['count'] == 2
    assert decoded['observations'][0]['raw_offset'] == first
    assert decoded['descriptors'][0][
        'record_layout'] == 'ascend_source_census_v2'
    assert decoded['descriptors'][0]['actor_stride'] == 64
    assert decoded['descriptors'][0]['program_stride'] == 192
    with pytest.raises(ValueError, match='raw length'):
        decode_shared_census(bytes(raw),
                             grid=[5],
                             actors=[actor],
                             capture_id='wrong-version',
                             invocation_id=None,
                             binary_id='fixture')
    corrupt = dict(plan, actor_stride=1024)
    with pytest.raises(ValueError, match='versioned physical ABI'):
        validate_transport(bytes(raw), corrupt, {1: actor['sites']})
    with pytest.raises(ValueError, match='columns'):
        validate_transport(bytes(raw), plan,
                           {1: [dict(site=77, role='primary', column=8)]})
