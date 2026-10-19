"""Lossless derived-view compaction and bounded, explicit reference loading."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture
def metadata(monkeypatch):
    package = ModuleType('bundle_metadata_test')
    package.__path__ = [
        str(Path(__file__).parents[1] / 'python/flagtree_profiler')
    ]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return importlib.import_module(package.__name__ + '.bundle_metadata')


@pytest.fixture
def bundle(tmp_path, metadata):
    compiler = dict(resources={'opaque': 'X' * 12000},
                    user={metadata.MARKER: {
                        'not': 'a registered reference'
                    }})
    mapping = dict(mapping=dict(resources=dict(values=compiler),
                                sites=[dict(label='Y' * 12000)]))
    binaries = [
        dict(id='binary-1',
             compiler_metadata=compiler,
             execution_manifest=mapping)
    ]
    original = {
        'ai/execution.json': dict(schema_version=1, binaries=[mapping]),
        'ai/binaries.json': binaries,
        'report/report.json': dict(backend='example', binaries=binaries),
    }
    for name, value in original.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(metadata.canonical(value) + b'\n')
    raw = tmp_path / 'raw/device.bin'
    raw.parent.mkdir()
    raw.write_bytes(b'original raw bytes')
    return tmp_path, copy.deepcopy(original)


def test_exact_roundtrip_and_smaller_bundle(metadata, bundle):
    root, original = bundle
    raw = (root / 'raw/device.bin').read_bytes()
    execution = (root / 'ai/execution.json').read_bytes()
    before = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    metadata.compact_timeline_metadata(root)
    for name, expected in original.items():
        assert metadata.load_bundle_json(root, name) == expected
    assert (root / 'ai/execution.json').read_bytes() == execution
    assert (root / 'raw/device.bin').read_bytes() == raw
    assert sum(p.stat().st_size for p in root.rglob('*')
               if p.is_file()) < before
    catalog = json.loads((root / metadata.CATALOG).read_text())
    assert sum(len(row['references'])
               for row in catalog['files'].values()) == 3
    with pytest.raises(ValueError, match='overwrite'):
        metadata.compact_timeline_metadata(root)


def test_legacy_and_unregistered_user_marker_are_literal(metadata, bundle):
    root, original = bundle
    for name, value in original.items():
        assert metadata.load_bundle_json(root, name) == value


def test_nonidentical_metadata_is_not_inferred(metadata, bundle):
    root, original = bundle
    binary = original['ai/binaries.json'][0]
    binary['compiler_metadata'] = dict(different='Z' * 12000)
    for name in ('ai/binaries.json', 'report/report.json'):
        (root / name).write_bytes(metadata.canonical(original[name]) + b'\n')
    metadata.compact_timeline_metadata(root)
    assert metadata.load_bundle_json(
        root, 'ai/binaries.json') == original['ai/binaries.json']
    catalog = json.loads((root / metadata.CATALOG).read_text())
    pointers = [
        r['pointer']
        for r in catalog['files']['ai/binaries.json']['references']
    ]
    assert '/0/compiler_metadata' not in pointers


@pytest.mark.parametrize('fault', [
    'file_digest', 'target_digest', 'pointer', 'cycle', 'external_path',
    'overlap', 'version'
])
def test_corrupt_references_are_rejected(metadata, bundle, fault):
    root, _ = bundle
    metadata.compact_timeline_metadata(root)
    catalog_path = root / metadata.CATALOG
    catalog = json.loads(catalog_path.read_text())
    refs = catalog['files']['report/report.json']['references']
    ref = refs[0]
    if fault == 'file_digest':
        (root / 'ai/execution.json').write_text('{}')
    elif fault == 'version':
        catalog['schema_version'] = True
    elif fault == 'overlap':
        refs.append(copy.deepcopy(ref))
    else:
        if fault == 'target_digest':
            ref['sha256'] = '0' * 64
        elif fault == 'pointer':
            ref['target_pointer'] = '/missing'
        elif fault == 'cycle':
            ref['file'] = 'report/report.json'
        elif fault == 'external_path':
            ref['file'] = '../outside.json'
        document = json.loads((root / 'report/report.json').read_text())
        document['binaries'] = {
            metadata.MARKER: {
                key: ref[key]
                for key in ('file', 'target_pointer', 'sha256')
            }
        }
        raw = metadata.canonical(document) + b'\n'
        (root / 'report/report.json').write_bytes(raw)
        catalog['files']['report/report.json']['sha256'] = hashlib.sha256(
            raw).hexdigest()
    catalog_path.write_bytes(metadata.canonical(catalog) + b'\n')
    with pytest.raises(ValueError):
        metadata.load_bundle_json(root, 'report/report.json')


def test_symlink_escape_is_rejected(metadata, bundle, tmp_path_factory):
    root, _ = bundle
    outside = tmp_path_factory.mktemp('external') / 'execution.json'
    outside.write_text('{}')
    (root / 'ai/execution.json').unlink()
    (root / 'ai/execution.json').symlink_to(outside)
    with pytest.raises(ValueError, match='escapes'):
        metadata.load_bundle_json(root, 'ai/execution.json')
