"""Local SYS duration proof contracts; real bundle validation is separate."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


def fixture(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        'raw_sys_fixture_for_source_clock',
        Path(__file__).with_name('test_cann_raw_sys.py'))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    raw_module, capture, receipts, raw, schema = helper.prepare(tmp_path)
    package = raw_module.__package__
    path = Path(__file__).resolve(
    ).parents[1] / 'python/flagtree_profiler/cann_source_clock.py'
    spec = importlib.util.spec_from_file_location(
        package + '.cann_source_clock', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    info_path = capture / 'device_4/info.json.4'
    info = json.loads(info_path.read_text())
    info['DeviceInfo'][0]['hwts_frequency'] = '50.000000'
    info_path.write_text(json.dumps(info))
    receipt_doc = json.loads(receipts.read_text())
    seal = json.loads(
        receipt_doc['receipts'][0]['sdk_capture_binding_evidence'])
    seal['device_info_snapshot'] = info
    receipt_doc['receipts'][0]['sdk_capture_binding_evidence'] = json.dumps(
        seal)
    receipts.write_text(json.dumps(receipt_doc))
    proof = module.build_native_task_proofs(capture, receipts)
    item = proof['task_identity_proofs'][0]
    analysis = tmp_path / 'sdk/tools/profiler/profiler_tool/analysis'
    analysis.mkdir(parents=True)
    monkeypatch.setattr(module, '_analysis_directory', lambda unused: analysis)
    header = tmp_path / 'sdk' / module._GETTER_HEADER
    header.parent.mkdir(parents=True)
    header.write_text(
        'inline int64_t GetSystemCycleImpl()\n{\n asm volatile("MOV %0, SYS_CNT");\n}\n'
    )
    llvm = tmp_path / 'adapted.ll'
    llvm.write_text('call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()\n')
    digest = hashlib.sha256(llvm.read_bytes()).hexdigest()
    binary = {
        'id': 'actual-compiler-hash',
        'compiler_metadata': {
            'arch': 'Ascend910B4-1',
            'flagprism_ascend_handoff': {
                'phase':
                'finished',
                'returncode':
                0,
                'compile_id':
                'compiled-case',
                'artifacts': [{
                    'driver_job': {
                        'state':
                        'finished',
                        'exit_code':
                        0,
                        'actor_kind':
                        'AIV',
                        'target_arch':
                        'dav-c220-vec',
                        'inputs': [{
                            'adapted_path': str(llvm),
                            'adapted_sha256': digest,
                            'pass_returncode': 0
                        }]
                    },
                    'metadata': {
                        'dynamic_clock': {
                            'domain': 'ascend.SYS_CNT'
                        }
                    },
                    'adapted': {
                        'path': str(llvm),
                        'sha256': digest,
                        'llir': llvm.read_text(),
                        'representation': 'instrumented_llvm_compiled_by_sdk'
                    }
                }]
            }
        }
    }
    identity = {
        key: item[key]
        for key in ('invocation_id', 'binary_id', 'scope_id', 'session_id',
                    'capture_epoch', 'token_id', 'status', 'evidence_kind')
    }
    vendor = {
        'binaries': [binary],
        'associations': [{
            'source': 'cann_sdk_task',
            'invocation_identity': identity,
            'metrics': {
                'sdk_task': item['native']['sdk_task']
            }
        }]
    }
    event = {
        'source': 'ascend_llvm_dynamic64',
        'association_status': 'verified',
        'invocation_id': item['invocation_id'],
        'association_evidence': {
            'invocation_id': item['invocation_id'],
            'binary_id': item['binary_id'],
            'scope_id': 0
        },
        'actor_slot': 1,
        'start_tick': 10,
        'end_tick': 30,
        'clock': {
            'domain': 'ascend.SYS_CNT',
            'scope': 'actor_local',
            'alignment': 'instance_local',
            'tick_ns': None
        }
    }
    return module, {'observations': [event]}, vendor, proof


def test_rate_supplies_only_local_duration_and_does_not_mutate_input(
        tmp_path, monkeypatch):
    module, observations, vendor, proof = fixture(tmp_path, monkeypatch)
    before = deepcopy(observations)
    output = module.calibrate_source_durations(observations, vendor, proof)
    event = output['observations'][0]
    assert event['duration_ns'] == 400
    assert event['clock']['tick_ns'] == 20
    assert event['clock']['alignment'] == 'instance_local'
    assert event['clock']['conversion_evidence'][
        'reported_hwts_frequency_mhz'] == '50.000000'
    assert event['relative_start_ns'] is None and 'origin_tick' not in event[
        'clock']
    assert observations == before


@pytest.mark.parametrize('failure', [
    'wrong_binary', 'wrong_invocation', 'bad_receipt_sha', 'duplicate_task',
    'non_a2', 'bad_llir_sha', 'missing_mov', 'wrong_actor', 'bad_rate',
    'bad_header', 'missing_llvm', 'changed_seal'
])
def test_missing_or_inconsistent_evidence_retains_unknown_duration(
        tmp_path, monkeypatch, failure):
    module, observations, vendor, proof = fixture(tmp_path, monkeypatch)
    event = observations['observations'][0]
    metadata = vendor['binaries'][0]['compiler_metadata']
    adapted = metadata['flagprism_ascend_handoff']['artifacts'][0]['adapted']
    info_path = Path(proof['capture_root']) / 'device_4/info.json.4'
    if failure == 'wrong_binary':
        event['association_evidence']['binary_id'] = 'other'
    elif failure == 'wrong_invocation':
        event['invocation_id'] = 'other'
    elif failure == 'bad_receipt_sha':
        proof['receipt_sha256'] = '0' * 64
    elif failure == 'duplicate_task':
        vendor['associations'] *= 2
    elif failure == 'non_a2':
        metadata['arch'] = 'Ascend950'
    elif failure == 'bad_llir_sha':
        adapted['sha256'] = '0' * 64
    elif failure == 'missing_mov':
        adapted['llir'] = 'ret void\n'
    elif failure == 'wrong_actor':
        event['actor_slot'] = 0
    elif failure == 'bad_rate':
        original = module._local_rate

        def changed_rate(item, root):
            altered = deepcopy(item)
            info = json.loads(info_path.read_text())
            info['DeviceInfo'][0]['hwts_frequency'] = '100'
            info_path.write_text(json.dumps(info))
            altered['sdk_capture_binding_evidence'][
                'device_info_snapshot'] = info
            return original(altered, root)

        monkeypatch.setattr(module, '_local_rate', changed_rate)
    elif failure == 'bad_header':
        header = module._analysis_directory(
            None).parents[3] / module._GETTER_HEADER
        header.write_text(
            'inline int64_t GetSystemCycleImpl()\n{\n return 0;\n}\n')
    elif failure == 'missing_llvm':
        Path(adapted['path']).unlink()
    elif failure == 'changed_seal':
        info_path.write_text('{}')
    result = module.calibrate_source_durations(observations, vendor,
                                               proof)['observations'][0]
    assert result['duration_ns'] is None
    assert result['clock']['tick_ns'] is None
    assert result['conversion_rejection_reason']


def test_other_backend_observation_is_unchanged(tmp_path, monkeypatch):
    module, observations, vendor, proof = fixture(tmp_path, monkeypatch)
    observations['observations'][0]['source'] = 'nvidia_device_clock'
    assert module.calibrate_source_durations(observations, vendor,
                                             proof) == observations


def test_independently_verified_shared_clock_is_unchanged(
        tmp_path, monkeypatch):
    module, observations, vendor, proof = fixture(tmp_path, monkeypatch)
    event = observations['observations'][0]
    event['clock'].update(alignment='verified_shared',
                          tick_ns=20,
                          origin_tick=1,
                          alignment_evidence={'independent': True})
    event.update(duration_ns=400, relative_start_ns=180)
    assert module.calibrate_source_durations(observations, vendor,
                                             proof) == observations
