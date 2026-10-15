"""Derived exports retain exact evidence through checked references."""
import copy
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'export_refs_test',
    Path(__file__).parents[1] / 'python/flagtree_profiler/export_refs.py')
refs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(refs)


def test_lossless_roundtrip_and_public_actor_clock_unchanged():
    capture = {
        'capture_id': 'capture-1',
        'raw_base64': 'a' * 4096,
        'dropped': 7,
        'runtime_metadata': {
            'binary_id': 'binary-1'
        }
    }
    clock = {'domain': 'counter', 'conversion_evidence': 'proof' * 512}
    original = {'captures': [capture], 'observations': [{'clock': clock}]}
    view = {
        'captures': [capture],
        'records': [{
            'clock': clock,
            'compiler_actor': {
                'identity': 'actor'
            },
            'source_links': []
        }]
    }
    before = copy.deepcopy(view)
    exported = refs.compact(view, original, fields={'raw_base64'})
    assert refs.restore(exported, original) == before
    assert view == before
    assert exported['records'] == before['records']
    assert len(refs.canonical(exported)) < len(refs.canonical(view))
    assert exported['captures'][0]['dropped'] == 7
    changed = copy.deepcopy(original)
    changed['captures'][0]['raw_base64'] += 'b'
    with pytest.raises(ValueError, match='artifact digest'):
        refs.restore(exported, changed)
    exported['captures'][0]['raw_base64']['$observation_ref'][
        'sha256'] = '0' * 64
    with pytest.raises(ValueError, match='field digest'):
        refs.restore(exported, original)


def test_pointer_escaping_and_nested_reconstruction_fields():
    evidence = {'a/b~c': 'x' * 1024}
    original = {'a/b~c': evidence}
    view = {'groups': [{'clock': evidence}]}
    exported = refs.compact(view, original, fields={'clock'})
    assert '~1' in exported['groups'][0]['clock']['$observation_ref'][
        'pointer']
    assert refs.restore(exported, original) == view


@pytest.mark.parametrize('key,value', [('schema_version', 2),
                                       ('schema_version', True),
                                       ('digest_encoding', 'unknown'),
                                       ('pointer_encoding', 'unknown')])
def test_unknown_reference_contract_is_rejected(key, value):
    original = {'raw_base64': 'x' * 1024}
    exported = refs.compact(original, original, fields={'raw_base64'})
    exported['export_references'][key] = value
    with pytest.raises(ValueError, match='reference contract'):
        refs.restore(exported, original)


@pytest.mark.parametrize('pointer', [
    'captures/0', '/captures/-1', '/captures/00', '/captures/1',
    '/captures/~2', '/missing'
])
def test_non_rfc6901_or_missing_pointer_is_rejected(pointer):
    original = {'captures': [{'raw_base64': 'x' * 1024}]}
    exported = refs.compact(original, original, fields={'raw_base64'})
    ref = exported['captures'][0]['raw_base64']['$observation_ref']
    ref.update(pointer=pointer, sha256=refs.digest(original))
    with pytest.raises(ValueError,
                       match='reference pointer|reference array index'):
        refs.restore(exported, original)
