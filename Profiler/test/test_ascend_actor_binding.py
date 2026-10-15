"""CPU fixtures validate provenance/slot joins, not accelerator execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).parents[1] / 'python/flagtree_profiler'
PACKAGE = '_ascend_binding_tests'
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package


def load(name):
    spec = importlib.util.spec_from_file_location(PACKAGE + '.' + name,
                                                  ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


helper = load('ascend_actor_binding')
decoder = load('observations_ascend')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fixture(kind='AIV'):
    original, adapted = 'original fixture LLVM', 'adapted fixture LLVM'
    binding = {
        'schema_version': 1,
        'function': 'actor',
        'actor_kind': kind,
        'layout': 'actor_header4_record8_v1',
        'segment_count': 3,
        'segment_words': 12,
        'record_actor_word': 5,
        'admissible_slots': [0] if kind == 'AIC' else [1, 2],
        'expression': {
            'kind': 'constant_i64',
            'value': 0
        } if kind == 'AIC' else {
            'kind': 'add_i64',
            'call': 'llvm.hivm.GET.SUBBLOCKID',
            'constant': 1
        },
        'value_use': 'same_emitted_i64_for_segment_offset_and_record_word5',
        'basis': 'actual_emitted_logger_actor_value',
        'module_sha256': digest(original),
        'compile_id': 'compile'
    }
    site = {
        'site_id': 9,
        'semantics': 'loop_header_occurrence',
        'public_semantic': 'control_checkpoint'
    }
    manifest = {
        'module_sha256':
        digest(original),
        'compile_id':
        'compile',
        'runtime_actor_binding':
        binding,
        'actors': [{
            'function': 'actor',
            'actor_kind': kind,
            'dynamic_observation_prepared': True
        }],
        'dynamic_sites': [site],
        'control_plan': {
            'inventory': [dict(site, selected=True)]
        }
    }
    artifact = {
        'metadata': manifest,
        'llir': original,
        'sha256': digest(original),
        'adapted': {
            'llir': adapted,
            'sha256': digest(adapted)
        }
    }
    handoff = {'compile_id': 'compile', 'artifacts': [artifact]}
    seal(handoff)
    return handoff


def seal(handoff):
    for artifact in handoff['artifacts']:
        text = json.dumps(artifact['metadata'])
        artifact.update(manifest_text=text, manifest_sha256=digest(text))


def raw(slot):
    words = [0] * 36
    words[slot * 12:(slot + 1) * 12] = [
        1, 1, 1, 0, (3 << 32) | 9, 0, 50, 50, 0, slot, (1 << 64) - 1,
        (1 << 64) - 1
    ]
    return words


@pytest.mark.parametrize('kind,slot', [('AIC', 0), ('AIV', 1), ('AIV', 2)])
def test_actual_slot_matches_emitted_admissible_set(kind, slot):
    sites = helper.bind_compiler_sites(fixture(kind), require_binding=True)
    result = decoder.decode_dynamic64(raw(slot),
                                      capacity=1,
                                      capture_id='fixture',
                                      site_manifest=sites,
                                      require_actor_binding=True)
    event, = result['observations']
    proof = event['compiler_site']['compiler_actor']['binding_proof']
    assert event['actor_slot'] == slot == proof['observed_actor_slot']
    assert proof[
        'runtime_slot_status'] == 'verified_against_raw_record_and_segment'
    assert result['actors'][slot][
        'binding_status'] == 'verified_by_committed_records'
    assert all(actor['execution_status'] == 'unknown'
               and actor['binding_status'] == 'unknown_no_records'
               for actor in result['actors'] if actor['actor_slot'] != slot)


@pytest.mark.parametrize('change', [
    'manifest', 'original', 'adapted', 'compile', 'slot', 'expression',
    'membership', 'duplicate'
])
def test_invalid_provenance_or_ambiguous_join_is_fail_closed(change):
    handoff = fixture()
    artifact = handoff['artifacts'][0]
    binding = artifact['metadata']['runtime_actor_binding']
    if change == 'manifest':
        artifact['manifest_text'] += ' '
    elif change == 'original':
        artifact['llir'] += 'changed'
    elif change == 'adapted':
        artifact['adapted']['llir'] += 'changed'
    elif change == 'compile':
        handoff['compile_id'] = 'different'
    elif change == 'slot':
        binding['admissible_slots'] = [1]
    elif change == 'expression':
        binding['expression']['constant'] = 0
    elif change == 'membership':
        artifact['metadata']['control_plan']['inventory'][0][
            'selected'] = False
    elif change == 'duplicate':
        handoff['artifacts'].append(copy.deepcopy(artifact))
    if change in ('slot', 'expression', 'membership'):
        seal(handoff)
    with pytest.raises(ValueError):
        helper.bind_compiler_sites(handoff, require_binding=True)


def test_wrong_raw_slot_or_ambiguous_site_is_rejected():
    sites = helper.bind_compiler_sites(fixture(), require_binding=True)
    for records, manifest in [(raw(0), sites), (raw(1), sites + sites)]:
        with pytest.raises(ValueError, match='unambiguous'):
            decoder.decode_dynamic64(records,
                                     capacity=1,
                                     capture_id='fixture',
                                     site_manifest=manifest,
                                     require_actor_binding=True)


def test_legacy_is_explicitly_unverified_and_auto_requires_binding():
    handoff = fixture()
    del handoff['artifacts'][0]['metadata']['runtime_actor_binding']
    assert helper.bind_compiler_sites(handoff) == []
    with pytest.raises(ValueError, match='lacks runtime actor binding'):
        helper.bind_compiler_sites(handoff, require_binding=True)
    event, = decoder.decode_dynamic64(raw(1), capacity=1,
                                      capture_id='fixture')['observations']
    assert event['compiler_actor_status'] == 'unverified_legacy'


def test_decoder_rechecks_capacity_and_recorded_actor():
    sites = helper.bind_compiler_sites(fixture(), require_binding=True)
    for site in sites:
        site['compiler_actor']['runtime_actor_binding']['segment_words'] = 20
    with pytest.raises(ValueError, match='runtime binding'):
        decoder.decode_dynamic64(raw(1),
                                 capacity=1,
                                 capture_id='fixture',
                                 site_manifest=sites,
                                 require_actor_binding=True)
