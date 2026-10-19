"""CPU contract fixtures, not Ascend compiler, timer or device qualification."""
import base64
import copy
import hashlib
import json
import struct

import pytest
from flagtree.profiler.timeline_ascend import plan_ascend_storage
from flagtree.profiler.timeline_events_ascend import (
    canonicalize_ascend_capture, compiler_actors, COMMIT, MAGIC)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture():
    tracked = [
        dict(opId=1, scopeId=0, sourceLoc='fixture:1',
             mlirOpName='arith.addf'),
        dict(opId=2, scopeId=0, sourceLoc='fixture:2', mlirOpName='tt.store')
    ]
    original = 'define void @fixture() { ret void }\n'
    adapted = '; explicit synthetic SDK output fixture, not machine evidence\n'
    binding = dict(schema_version=1,
                   actor_kind='AIV',
                   function='fixture',
                   layout='ascend_source_timeline_v1',
                   compile_id='compile-fixture',
                   module_sha256=sha(original.encode()),
                   header_bytes=64,
                   record_bytes=64,
                   segment_count=3,
                   segment_words=24,
                   max_program_slots=2,
                   selection='runtime_first_last',
                   admissible_slots=[1, 2],
                   expression=dict(kind='add_i64',
                                   call='llvm.hivm.GET.SUBBLOCKID',
                                   constant=1),
                   frontend_carrier='source_census_site.v3',
                   source_program_binding=dict(
                       basis='actual_selected_source_site_marker_operands',
                       linear_expression='x + grid_x * (y + grid_y * z)',
                       anchors=[
                           dict(source_op_id=i,
                                census_column=i - 1,
                                source_site_count=2,
                                operands=['x', 'y', 'z', 'gx', 'gy', 'gz'],
                                operand_roles=[
                                    'x', 'y', 'z', 'grid_x', 'grid_y', 'grid_z'
                                ]) for i in [1, 2]
                       ]))
    manifest = dict(compile_id='compile-fixture',
                    module_sha256=sha(original.encode()),
                    runtime_actor_binding=binding,
                    actors=[
                        dict(function='fixture',
                             actor_kind='AIV',
                             dynamic_observation_prepared=True)
                    ],
                    dynamic_sites=[
                        dict(site_id=i,
                             source_op_id=i,
                             frontend_column=i - 1,
                             public_semantic='source_control_interval',
                             semantic_code=1,
                             operation_class='lowered_source_fragment',
                             boundary_status='unverified',
                             original_instructions='fixture ' + str(i),
                             original_instructions_sha256=sha(
                                 ('fixture ' + str(i)).encode()),
                             scope='fixture_block_fragment',
                             original_block='entry') for i in [1, 2]
                    ])
    text = json.dumps(manifest)
    binary = b'explicit binary fixture'
    meta = dict(
        hash='a' * 64,
        debug_record_layout='ascend_source_timeline_v1',
        debug_record_capacity=2,
        debug_record_size=64,
        debug_records_per_instance=6,
        debug_timeline_storage_version=1,
        debug_timeline_publisher_version=1,
        flagprism_ascend_source_timeline_version=1,
        debug_frontend_marker_abi=dict(version=3,
                                       record_layout='ascend_source_census_v3',
                                       site_count=2),
        debug_automatic_plan=dict(selected_sites=[1, 2]),
        debug_census_columns=2,
        debug_tracked_table=tracked,
        flagprism_ascend_observation_request=dict(
            program_policy='runtime_first_last',
            programs=None,
            automatic=True,
            semantics=['source_control_interval'],
            sample_every=1,
            max_events_per_instance=2),
        flagprism_ascend_handoff=dict(
            phase='finished',
            returncode=0,
            compile_id='compile-fixture',
            source_snapshot=dict(ir='fixture',
                                 ir_sha256=sha(b'fixture'),
                                 tracked_ops_sha256=sha(
                                     json.dumps(tracked,
                                                sort_keys=True,
                                                separators=(',',
                                                            ':')).encode())),
            final_outputs=dict(
                binary=dict(encoding='base64',
                            data=base64.b64encode(binary).decode(),
                            bytes=len(binary),
                            sha256=sha(binary))),
            artifacts=[
                dict(metadata=manifest,
                     manifest_text=text,
                     manifest_sha256=sha(text.encode()),
                     llir=original,
                     sha256=sha(original.encode()),
                     adapted=dict(llir=adapted, sha256=sha(adapted.encode())))
            ]))
    plan = dict(binary_id=meta['hash'],
                compiler_metadata=meta,
                runtime_metadata=dict(
                    grid=[3, 3, 1], record_layout=meta['debug_record_layout']))
    layout = plan_ascend_storage(plan,
                                 grid=[3, 3, 1],
                                 scratch_size=192,
                                 alignment=64,
                                 num_ctas=None,
                                 max_raw_bytes=8388608)
    owner = dict(capture_id='capture-fixture',
                 invocation_id='invocation-fixture',
                 binary_id=meta['hash'],
                 plan=plan,
                 layout=layout,
                 submission_outcome='returned')
    association = dict(evidence='same_launch_metadata_object',
                       binary_id=meta['hash'],
                       invocation_id='launch-fixture',
                       scope_id=7,
                       session_ids=[1])
    raw = bytearray(layout['raw_bytes'])
    for slot, program in enumerate([0, 8]):
        base = (slot * 3 + 1) * 192
        physical = 3 + slot
        struct.pack_into('<8Q', raw, base, MAGIC, 2, 2, 0, program, 1,
                         physical, 1)
        for n in range(2):
            descriptor = (n + 1) | (1 << 32)
            tag = COMMIT ^ descriptor ^ n ^ program ^ 1 ^ physical
            struct.pack_into('<8Q', raw, base + 64 + n * 64, descriptor, n,
                             100 + n * 20, 110 + n * 20, program, 1, physical,
                             tag)
    return meta, owner, association, bytes(raw)


def decode(meta, owner, association, raw):
    return canonicalize_ascend_capture(raw,
                                       owner=owner,
                                       metadata=meta,
                                       association=association)


def test_raw_pairs_keep_actual_coordinates_offsets_and_unknown_actors():
    meta, owner, association, raw = fixture()
    batch = decode(meta, owner, association, raw)
    assert len(batch['events']) == 4 and len(batch['records']) == 8
    assert batch['clock_status'] == batch['boundary_status'] == 'unverified'
    assert not batch['complete']
    observed = [o for o in batch['observers'] if o['retained_records']]
    assert [o['program_coordinates'] for o in observed] == [[0, 0, 0],
                                                            [2, 2, 0]]
    assert [o['physical_identity']['ascend.block_id']
            for o in observed] == [3, 4]
    assert sum(o['attributes']['ascend.writer_state'] == 'unobserved'
               for o in batch['observers']) == 2
    for r in batch['records']:
        assert struct.unpack_from('<Q', raw, r['offset'])[0] == r['tick']


@pytest.mark.parametrize('change', [
    'commit', 'unknown_site', 'counter', 'unassigned', 'truncated',
    'negative_duration'
])
def test_bad_raw_is_rejected_without_modification(change):
    meta, owner, association, raw = fixture()
    bad = bytearray(raw)
    base = 192
    if change == 'commit': bad[base + 64 + 56] ^= 1
    elif change == 'unknown_site':
        struct.pack_into('<Q', bad, base + 64, (1 << 32) | 999)
    elif change == 'counter':
        struct.pack_into('<Q', bad, base + 16, 4)
    elif change == 'unassigned':
        bad[0] = 1
    elif change == 'truncated':
        bad = bad[:-8]
    else:
        struct.pack_into('<Q', bad, base + 64 + 16, 111)
    with pytest.raises(ValueError):
        decode(meta, owner, association, bytes(bad))
    assert len(raw) == 1152


@pytest.mark.parametrize('field,value',
                         [('debug_timeline_storage_version', True),
                          ('debug_record_capacity', True), ('hash', 'b' * 64)])
def test_component_identity_mismatch_rejected(field, value):
    meta, owner, association, raw = fixture()
    meta[field] = value
    with pytest.raises(ValueError):
        decode(meta, owner, association, raw)


def test_real_physical_budget_and_source_provenance_are_required():
    meta, owner, association, raw = fixture()
    with pytest.raises(ValueError):
        plan_ascend_storage(owner['plan'],
                            grid=[3, 3, 1],
                            scratch_size=192,
                            alignment=64,
                            num_ctas=None,
                            max_raw_bytes=1151)
    meta['flagprism_ascend_handoff']['artifacts'][0]['adapted'][
        'llir'] = 'changed'
    with pytest.raises(ValueError):
        compiler_actors(meta)


def test_empty_slot_cannot_be_relabelled_as_complete():
    meta, owner, association, raw = fixture()
    batch = decode(meta, owner, association, raw)
    for observer in batch['observers']:
        if observer['attributes']['ascend.writer_state'] == 'unobserved':
            assert observer['retained_records'] == 0 and observer[
                'physical_identity'] is None and not observer['complete']


def test_reexport_from_original_requires_no_device_and_keeps_raw(tmp_path):
    from flagtree.profiler.timeline_reexport import reexport_capture
    meta, owner, association, raw = fixture()
    directory = tmp_path / 'timeline'
    (directory / 'captures').mkdir(parents=True)
    path = 'captures/' + owner['invocation_id']
    (directory / (path + '.raw')).write_bytes(raw)
    original = dict(owner=owner,
                    launch=association,
                    metadata=dict(compiler_metadata=meta),
                    raw_file=path + '.raw',
                    raw_sha256=sha(raw))
    (directory / (path + '.input.json')).write_text(json.dumps(original))
    before = {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in directory.rglob('*') if p.is_file()
    }
    first = reexport_capture(directory, path + '.input.json')
    second = reexport_capture(directory, path + '.input.json')
    assert first['canonical_revision'] == second[
        'canonical_revision'] and first['status'] == 'raw_only'
    for name, data in before.items():
        assert (directory / name).read_bytes() == data


def test_two_compiler_functions_cannot_silently_share_one_log_slot():
    meta, owner, association, raw = fixture()
    artifacts = meta['flagprism_ascend_handoff']['artifacts']
    artifacts.append(copy.deepcopy(artifacts[0]))
    with pytest.raises(ValueError, match='alias'):
        compiler_actors(meta)


def test_same_volume_grid_cannot_change_source_coordinates_on_reexport():
    meta, owner, association, raw = fixture()
    owner['layout']['grid'] = [9, 1, 1]
    with pytest.raises(ValueError, match='geometry'):
        decode(meta, owner, association, raw)


@pytest.mark.parametrize('value', [True, 2, 1.0])
def test_unsampled_protocol_cannot_accept_another_sampling_rule(value):
    meta, owner, association, raw = fixture()
    meta['flagprism_ascend_observation_request']['sample_every'] = value
    with pytest.raises(ValueError):
        decode(meta, owner, association, raw)


@pytest.mark.parametrize('kind', ['early_drop', 'false_saturation'])
def test_loss_flags_must_follow_the_actual_publisher(kind):
    meta, owner, association, raw = fixture()
    bad = bytearray(raw)
    if kind == 'early_drop':
        struct.pack_into('<4Q', bad, 192, MAGIC, 1, 2, 1)
        struct.pack_into('<Q', bad, 192 + 56, 5)
        bad[192 + 128:192 + 192] = bytes(64)
    else:
        struct.pack_into('<Q', bad, 192 + 56, 3)
    with pytest.raises(ValueError):
        decode(meta, owner, association, bytes(bad))


# Synthetic ABI rejection fixtures. Real LLVM/device qualification is separate.
def native_fixture(operation):
    meta, owner, association, raw = fixture()
    artifact = meta['flagprism_ascend_handoff']['artifacts'][0]
    manifest = artifact['metadata']
    semantic = 2 if operation == 'set_flag' else 3
    intrinsic = 'llvm.hivm.' + ('SET'
                                if semantic == 2 else 'WAIT') + '.FLAG.IMM'
    original_call = '  call void @' + intrinsic + '(i64 1, i64 0, i64 0), !dbg !12'
    original = 'define void @fixture() {\n' + original_call.replace(
        '!dbg !12', '!dbg !40') + '\nret void\n}\n'
    artifact['llir'] = original
    artifact['sha256'] = sha(original.encode())
    manifest['module_sha256'] = sha(original.encode())
    manifest['runtime_actor_binding'].update(module_sha256=sha(
        original.encode()),
                                             native_control_version=1)
    manifest['dynamic_sites'][1].update(
        semantic_code=semantic,
        operation_class='native_control_scalar_bracket',
        native_operation=operation,
        intrinsic=intrinsic,
        native_arguments=[1, 0, 0],
        completion_status='unverified',
        scope='scalar_issue_of_original_native_control',
        source_binding='containing_original_block_fragment_navigation',
        original_instructions=original_call,
        original_instructions_sha256=sha(original_call.encode()))
    reseal_manifest(artifact)
    raw = bytearray(raw)
    for slot, program in enumerate([0, 8]):
        offset = (slot * 3 + 1) * 192 + 128
        descriptor = 2 | semantic << 32
        physical = 3 + slot
        struct.pack_into('<Q', raw, offset, descriptor)
        struct.pack_into('<Q', raw, offset + 56,
                         COMMIT ^ descriptor ^ 1 ^ program ^ 1 ^ physical)
    return meta, owner, association, bytes(raw)


def reseal_manifest(artifact):
    text = json.dumps(artifact['metadata'])
    artifact.update(manifest_text=text, manifest_sha256=sha(text.encode()))


@pytest.mark.parametrize('operation', ['set_flag', 'wait_flag'])
def test_versioned_native_controls_keep_exact_raw_and_honest_semantics(
        operation):
    meta, owner, association, raw = native_fixture(operation)
    batch = decode(meta, owner, association, raw)
    native = [
        s for s in batch['sites']
        if s['attributes'].get('ascend.native_operation') == operation
    ]
    assert native
    assert all(s['semantic'] == 'observer_region_elapsed'
               and s['attributes']['ascend.completion_status'] == 'unverified'
               and s['attributes']['ascend.engine_activity_verified'] is False
               for s in native)
    assert batch['clock_status'] == 'unverified'
    for r in batch['records']:
        assert struct.unpack_from('<Q', raw, r['offset'])[0] == r['tick']


@pytest.mark.parametrize('fault', [
    'missing_version', 'wrong_version', 'bool_version', 'arguments',
    'intrinsic', 'completion', 'source_binding', 'raw_semantic'
])
def test_native_controls_reject_forged_or_unversioned_bindings(fault):
    meta, owner, association, raw = native_fixture('wait_flag')
    artifact = meta['flagprism_ascend_handoff']['artifacts'][0]
    binding = artifact['metadata']['runtime_actor_binding']
    site = artifact['metadata']['dynamic_sites'][1]
    if fault == 'missing_version': binding.pop('native_control_version')
    elif fault == 'wrong_version': binding['native_control_version'] = 2
    elif fault == 'bool_version': binding['native_control_version'] = True
    elif fault == 'arguments': site['native_arguments'] = [4, 0, 0]
    elif fault == 'intrinsic': site['intrinsic'] = 'llvm.hivm.SET.FLAG.IMM'
    elif fault == 'completion': site['completion_status'] = 'verified'
    elif fault == 'source_binding': site['source_binding'] = 'guessed'
    else:
        raw = bytearray(raw)
        offset = 192 + 128
        descriptor = 2 | 1 << 32
        struct.pack_into('<Q', raw, offset, descriptor)
        struct.pack_into('<Q', raw, offset + 56,
                         COMMIT ^ descriptor ^ 1 ^ 0 ^ 1 ^ 3)
        raw = bytes(raw)
    reseal_manifest(artifact)
    with pytest.raises(ValueError):
        decode(meta, owner, association, raw)
