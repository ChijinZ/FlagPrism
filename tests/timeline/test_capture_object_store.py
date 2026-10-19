"""Storage integrity and bounded restoration, without a device or SDK."""
import copy
import json
from pathlib import Path
import zlib

import pytest

from flagtree.profiler import timeline_capture_store as store
from flagtree.profiler.timeline_store import json_bytes, sha256


def sample():
    return dict(owner=dict(invocation_id='one', binary_id='binary'),
                metadata=dict(
                    compiler={'ir': 'real-looking LLVM text\n' * 800},
                    rows=[{
                        'source': 'line',
                        'words': list(range(80))
                    }] * 40),
                user_dictionary={
                    '$flagprism_text_ref': 'literal, not a reference',
                    store.VERSION_KEY: 999,
                    'unicode': '中文📈'
                })


def header(root, name='captures/one.json'):
    return json.loads((root / name).read_text())


def save_header(root, value, name='captures/one.json'):
    (root / name).write_bytes(json_bytes(value))


def test_roundtrip_deduplicates_and_retains_actual_input_closure(tmp_path):
    value = sample()
    frozen = copy.deepcopy(value)
    store.persist_capture(tmp_path, 'captures/one.json', value)
    objects = sorted(tmp_path.glob('objects/capture/*'))
    need_count = len(objects)
    assert objects and sum(p.stat().st_size
                           for p in objects) < len(json_bytes(value))
    second = dict(value, owner=dict(invocation_id='two', binary_id='binary'))
    store.persist_capture(tmp_path, 'captures/two.json', second)
    assert len(list(tmp_path.glob('objects/capture/*'))) == need_count
    calls = []
    restored = store.load_capture(tmp_path,
                                  'captures/one.json',
                                  retain=lambda name, **kw: calls.append(
                                      (name, kw)))
    assert restored == frozen == value
    assert store.load_capture_file(tmp_path / 'captures/one.json') == value
    assert len(calls) == need_count + 1
    assert store.load_capture(tmp_path, 'captures/two.json') == second
    for name, identity in calls:
        raw = (tmp_path / name).read_bytes()
        assert identity == dict(digest=sha256(raw), size=len(raw))


def test_legacy_and_small_new_document_remain_plain_json(tmp_path):
    value = {
        'owner': {
            'invocation_id': 'old'
        },
        'user': {
            'references': ['literal']
        }
    }
    store.persist_capture(tmp_path, 'captures/one.json', value)
    assert header(tmp_path) == value
    assert store.load_capture(tmp_path, 'captures/one.json') == value
    assert not list(tmp_path.glob('objects/capture/*'))


def test_repeated_persist_is_immutable_and_missing_object_cannot_be_reused(
        tmp_path):
    value = sample()
    store.persist_capture(tmp_path, 'captures/one.json', value)
    before = {
        str(p.relative_to(tmp_path)): p.read_bytes()
        for p in tmp_path.rglob('*') if p.is_file()
    }
    store.persist_capture(tmp_path, 'captures/one.json', value)
    assert before == {
        str(p.relative_to(tmp_path)): p.read_bytes()
        for p in tmp_path.rglob('*') if p.is_file()
    }
    obj = next(tmp_path.glob('objects/capture/*'))
    obj.unlink()
    with pytest.raises(ValueError, match='Missing'):
        store.load_capture(tmp_path, 'captures/one.json')


@pytest.mark.parametrize('fault', [
    'version', 'extra', 'overlap', 'path', 'extent', 'digest', 'placeholder',
    'object_bytes', 'symlink'
])
def test_corrupt_reference_is_rejected(tmp_path, fault):
    store.persist_capture(tmp_path, 'captures/one.json', sample())
    doc = header(tmp_path)
    ref = doc['references'][0]
    if fault == 'version':
        doc[store.VERSION_KEY] = True
    elif fault == 'extra':
        ref['extra'] = 1
    elif fault == 'overlap':
        doc['references'].append(copy.deepcopy(ref))
    elif fault == 'path':
        ref['path'] = ['missing', -1]
    elif fault == 'extent':
        ref['decoded_bytes'] = True
    elif fault == 'digest':
        ref['decoded_sha256'] = '0' * 64
    elif fault == 'placeholder':
        ref['path'] = ['owner', 'binary_id']
    elif fault == 'object_bytes':
        (tmp_path / ref['file']).write_bytes(b'changed')
    elif fault == 'symlink':
        target = tmp_path / ref['file']
        raw = target.read_bytes()
        target.unlink()
        other = tmp_path / 'outside.zlib'
        other.write_bytes(raw)
        target.symlink_to(other)
    save_header(tmp_path, doc)
    with pytest.raises(ValueError):
        store.load_capture(tmp_path, 'captures/one.json')


@pytest.mark.parametrize(
    'fault', ['trailing', 'truncated', 'bomb', 'expansion', 'reference_count'])
def test_bounded_object_decoding(tmp_path, monkeypatch, fault):
    limit = 8192
    monkeypatch.setattr(store, 'LIMIT', limit)
    (tmp_path / 'captures').mkdir()
    envelope = store._envelope('x' * (limit + 1 if fault == 'bomb' else 3000),
                               [])
    raw = json_bytes(envelope)
    packed = zlib.compress(raw)
    if fault == 'trailing':
        packed += b'extra'
    elif fault == 'truncated':
        packed = packed[:-1]
    digest = sha256(packed)
    name = 'objects/capture/' + digest + '.json.zlib'
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes(packed)
    ref = dict(path=['a'],
               file=name,
               bytes=len(packed),
               sha256=digest,
               decoded_bytes=min(limit, len(raw)),
               decoded_sha256=sha256(raw))
    doc = store._envelope({'a': None}, [ref])
    if fault == 'expansion':
        doc = store._envelope([None, None, None],
                              [dict(ref, path=[i]) for i in range(3)])
    elif fault == 'reference_count':
        doc['references'] = [ref] * (store.MAX_REFERENCES + 1)
    save_header(tmp_path, doc)
    with pytest.raises(ValueError):
        store.load_capture(tmp_path, 'captures/one.json')


def test_writer_bounds_and_input_are_not_mutated(tmp_path, monkeypatch):
    value = sample()
    original = copy.deepcopy(value)
    monkeypatch.setattr(store, 'LIMIT', 100)
    with pytest.raises(ValueError, match='budget'):
        store.persist_capture(tmp_path, 'captures/one.json', value)
    assert original == value
    assert not list(tmp_path.rglob('*.zlib'))


def test_writer_does_not_publish_an_unreadable_near_limit_object(
        tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'LIMIT', 8192)
    value = {'blob': 'x' * (8192 - len(json_bytes({'blob': ''})))}
    assert len(json_bytes(value)) == store.LIMIT
    with pytest.raises(ValueError, match='object.*budget'):
        store.persist_capture(tmp_path, 'captures/one.json', value)
    assert not (tmp_path / 'captures/one.json').exists()
    assert not list(tmp_path.rglob('*.zlib'))


def test_writer_checks_cumulative_object_envelope_budget_before_publication(
        tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'LIMIT', 8192)
    value = {'a': 'x' * 4050, 'b': 'y' * 4050}
    assert len(json_bytes(value)) < store.LIMIT
    with pytest.raises(ValueError, match='object.*budget'):
        store.persist_capture(tmp_path, 'captures/one.json', value)
    assert not (tmp_path / 'captures/one.json').exists()
    assert not list(tmp_path.rglob('*.zlib'))


def test_legacy_inline_budget_is_not_reduced_to_new_header_budget(
        tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'HEADER_LIMIT', 64)
    monkeypatch.setattr(store, 'LIMIT', 8192)
    value = {'owner': {}, 'text': 'legacy' * 100}
    (tmp_path / 'captures').mkdir()
    save_header(tmp_path, value)
    assert store.load_capture_file(tmp_path / 'captures/one.json') == value
    save_header(tmp_path, store._envelope(value, []))
    with pytest.raises(ValueError, match='header'):
        store.load_capture_file(tmp_path / 'captures/one.json')


def test_failed_object_publication_leaves_no_capture_and_retry_recovers(
        tmp_path, monkeypatch):
    original = store.persist
    calls = []

    def fail(directory, relative, payload):
        calls.append(relative)
        if len(calls) == 2:
            raise OSError('injected object publication failure')
        original(directory, relative, payload)

    monkeypatch.setattr(store, 'persist', fail)
    value = sample()
    with pytest.raises(OSError, match='publication'):
        store.persist_capture(tmp_path, 'captures/one.json', value)
    assert not (tmp_path / 'captures/one.json').exists()
    monkeypatch.setattr(store, 'persist', original)
    store.persist_capture(tmp_path, 'captures/one.json', value)
    assert store.load_capture(tmp_path, 'captures/one.json') == value


def test_offline_original_includes_objects_in_authoritative_input_closure(
        tmp_path):
    from flagtree.profiler.timeline_reexport import _original
    value = sample()
    value['owner'].update(submission_outcome='returned',
                          layout={'raw_bytes': 4})
    value['raw_file'] = 'captures/one.raw'
    value['raw_sha256'] = sha256(b'raw!')
    (tmp_path / 'captures').mkdir()
    (tmp_path / value['raw_file']).write_bytes(b'raw!')
    name = 'captures/one.input.json'
    store.persist_capture(tmp_path, name, value)
    capture, raw, inputs, _ = _original(tmp_path, name)
    assert capture == value and raw == b'raw!'
    objects = {
        str(p.relative_to(tmp_path))
        for p in tmp_path.glob('objects/capture/*')
    }
    assert objects and objects <= set(inputs)
    for relative, identity in inputs.items():
        payload = (tmp_path / relative).read_bytes()
        assert identity == dict(sha256=sha256(payload), bytes=len(payload))
