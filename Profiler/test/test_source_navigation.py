"""Captured bytes, source roles and bounds govern navigable source anchors."""
import base64
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture
def modules(monkeypatch):
    package = ModuleType('source_navigation_test')
    package.__path__ = [
        str(Path(__file__).parents[1] / 'python/flagtree_profiler')
    ]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return [
        importlib.import_module(package.__name__ + '.' + name)
        for name in ('source_view', 'fine_grained', 'execution_view', 'native')
    ]


def test_compact_labels_preserve_source_identity_roles_and_navigation(modules):
    source = modules[0]
    record = dict(source_links=[
        dict(file='/capture/very/long/path/kernel.py',
             line=9,
             column=2,
             role=role,
             href='sources.html?source=sha-full#L9')
        for role in ('interval_entry', 'captured_location_reference')
    ])
    before = json.dumps(record, sort_keys=True)
    rendered = source.source_cell(record, compact=True)
    assert rendered.count('<a ') == 1
    assert '>kernel.py:9:2</a>' in rendered
    assert 'href="sources.html?source=sha-full#L9"' in rendered
    assert '/capture/very/long/path/kernel.py:9:2' in rendered
    assert 'interval entry' in rendered and 'captured location reference' in rendered
    assert 'aria-label=' in rendered
    assert json.dumps(record, sort_keys=True) == before
    # The existing full-label interface retains separate compiler source roles.
    assert source.source_cell(record).count('<a ') == 2


def snapshot(tmp_path,
             content=b'first\nsecond\nthird\n',
             reference='ai/original.py'):
    (tmp_path / 'ai').mkdir(exist_ok=True)
    (tmp_path / 'report').mkdir(exist_ok=True)
    (tmp_path / reference).write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    (tmp_path / 'ai/binaries.json').write_text(
        json.dumps([{
            'id': 'binary-a',
            'source': {
                'path': '/capture/kernel.py',
                'file_snapshot_file': reference,
                'file_sha256': digest
            }
        }]))
    return digest


def record(candidates):
    return dict(binary_id='binary-a', source_location_candidates=candidates)


def test_out_of_bounds_primary_preserves_valid_inline_callsite(
        modules, tmp_path):
    source, fine, _, _ = modules
    digest = snapshot(tmp_path)
    candidates = fine._location_candidates({
        'source_file':
        '/capture/kernel.py',
        'line':
        309,
        'column':
        36,
        'inline_chain': [{
            'directory': '/capture',
            'file': 'kernel.py',
            'line': 2,
            'column': 7
        }]
    })
    row = record(candidates)
    catalog = source.SourceCatalog(tmp_path)
    catalog.load([])
    catalog.annotate([row])
    catalog.write()
    primary, inline = row['source_location_candidates']
    assert primary['role'] == 'compiler_primary'
    assert primary['validation_status'] == 'outside_snapshot_line_range'
    assert 'href' not in primary
    assert inline['role'] == 'inline_callsite'
    assert inline['snapshot_sha256'] == digest
    assert inline['validation_status'] == 'in_range_snapshot_position'
    assert inline['href'].endswith('#L2')
    assert row['source_status'] == 'located'
    assert row['source_locations'] == [
        dict(file='/capture/kernel.py', line=2, column=7)
    ]
    cell = source.source_cell(row)
    assert 'inline callsite' in cell and 'outside snapshot line range' in cell
    assert '309:36</a>' not in cell
    assert len(
        json.loads(
            (tmp_path / 'ai/source_index.json').read_text())['sources']) == 1


@pytest.mark.parametrize('failure', ['digest', 'path_escape', 'basename_only'])
def test_unverified_snapshot_never_becomes_located(modules, tmp_path, failure):
    source = modules[0]
    snapshot(tmp_path)
    path = tmp_path / 'ai/binaries.json'
    binaries = json.loads(path.read_text())
    if failure == 'digest':
        binaries[0]['source']['file_sha256'] = '0' * 64
    elif failure == 'path_escape':
        binaries[0]['source']['file_snapshot_file'] = '../outside.py'
    path.write_text(json.dumps(binaries))
    row = record([
        dict(file='kernel.py'
             if failure == 'basename_only' else '/capture/kernel.py',
             line=2,
             column=1)
    ])
    catalog = source.SourceCatalog(tmp_path)
    catalog.load([])
    catalog.annotate([row])
    assert row['source_status'] == 'unresolved'
    assert row['source_links'] == []
    assert row['source_locations'] == []


def test_distinct_snapshot_versions_do_not_silently_choose_one(
        modules, tmp_path):
    source = modules[0]
    snapshot(tmp_path)
    alternate = b'other\ncontents\n'
    captures = [{
        'binary_id':
        'binary-a',
        'scope_origin_sources': [{
            'status':
            'captured',
            'file':
            '/capture/kernel.py',
            'sha256':
            hashlib.sha256(alternate).hexdigest(),
            'content':
            base64.b64encode(alternate).decode()
        }]
    }]
    row = record([dict(file='/capture/kernel.py', line=2, column=1)])
    catalog = source.SourceCatalog(tmp_path)
    catalog.load(captures)
    catalog.annotate([row])
    assert row['source_location_candidates'][0][
        'validation_status'] == 'ambiguous_snapshot_versions'
    assert not row['source_links']


def test_report_embeds_source_as_data_without_script_injection(
        modules, tmp_path):
    source = modules[0]
    snapshot(tmp_path, b'# </script><script>window.injection=1</script>\n')
    catalog = source.SourceCatalog(tmp_path)
    catalog.load([])
    catalog.write()
    page = (tmp_path / 'report/sources.html').read_text()
    assert '</script><script>window.injection' not in page
    assert '\\u003c/script\\u003e' in page
    assert 'document.createTextNode(text)' in page


def test_dynamic_identity_summary_keeps_calls_and_clock_frames_separate(
        modules):
    execution = modules[2]
    records = [
        dict(binary_id='b',
             invocation_id=call,
             actor=0,
             program=0,
             semantic='control_checkpoint',
             clock=dict(scope=scope),
             site=4,
             association_status='verified')
        for call, scope in [('call-a', 'clock-a'), (
            'call-a', 'clock-a'), ('call-b', 'clock-a'), ('call-a', 'clock-b')]
    ]
    page = execution.render(
        dict(binaries=[
            dict(binary_id='b',
                 backend='test',
                 mapping=dict(
                     execution_model='actual_model',
                     dependencies=[dict(from_site='<script>', to_site=9)]))
        ]), records)
    assert '<script>' not in page and '&lt;script&gt;' in page
    assert page.count('<td>call-a</td>') == 2
    assert page.count('<td>call-b</td>') == 1
    assert '<dt>4</dt><dd>2</dd>' in page
    assert 'Static and measured actor identifiers are not matched by name.' in page


def test_source_failure_is_actionable_and_does_not_blame_execution(
        modules, tmp_path):
    fine = modules[1]
    (tmp_path / 'ai').mkdir()
    (tmp_path / 'ai/fine_grained.json').write_text(
        json.dumps(
            dict(captures=[
                dict(capture_id='capture-a',
                     invocation_id='launch-a',
                     binary_id='binary-a')
            ],
                 records=[
                     dict(capture_id='capture-a',
                          invocation_id='launch-a',
                          binary_id='binary-a',
                          source_locations=[],
                          operation='arith.addf',
                          association_status='verified',
                          semantic='operation_checkpoint')
                 ])))
    with pytest.raises(RuntimeError, match='lack_valid_source_snapshot'):
        fine.require_automatic_records(tmp_path, {'automatic': True})
    status = json.loads((tmp_path / 'ai/selection_status.json').read_text())
    assert 'source_index.json' in status['action']
    assert 'conditional work' not in status['action']


@pytest.mark.parametrize('entry', ['runtime_binding', 'compiler_binding'])
def test_native_loader_preserves_original_module_error(modules, monkeypatch,
                                                       entry):
    native = modules[3]
    original = OSError(
        'libdependent_test.so: undefined symbol: missing_test_symbol')

    def fail(name):
        raise original

    monkeypatch.setattr(native.importlib, 'import_module', fail)
    with pytest.raises(RuntimeError) as result:
        getattr(native, entry)()
    assert result.value.__cause__ is original
    assert 'missing_test_symbol' in str(result.value)
    assert 'triton._C.libtriton' in str(result.value)


def test_external_helper_snapshots_preserve_raw_bytes_and_do_not_reopen_sources(
        modules, tmp_path):
    capture = importlib.import_module(modules[0].__package__ +
                                      '.source_capture')
    helper = tmp_path / 'helper.py'
    content = b'# coding: latin-1\r\n# caf\xe9\r\ndef helper():\r\n    return 1\r\n'
    helper.write_bytes(content)
    snapshots = capture.capture_metadata_sources(
        {'sourceLoc': f'loc("{helper}":3:1)'}, {
            'inline_chain': [{
                'directory': str(tmp_path),
                'file': 'helper.py',
                'line': 3,
                'column': 1
            }]
        })
    assert len(snapshots) == 1
    assert base64.b64decode(snapshots[0]['content']) == content
    helper.unlink()
    output = tmp_path / 'bundle'
    (output / 'ai').mkdir(parents=True)
    (output / 'report').mkdir()
    exported = capture.export_metadata_sources(snapshots, output)
    assert 'content' not in exported[0]
    (output / 'ai/binaries.json').write_text(
        json.dumps([dict(id='binary-a', source_snapshots=exported)]))
    catalog = modules[0].SourceCatalog(output)
    catalog.load([])
    row = record([dict(file=str(helper), line=3, column=1)])
    catalog.annotate([row])
    catalog.write()
    assert row['source_status'] == 'located'
    assert row['source_links'][0]['snapshot_line_count'] == 4
    assert 'caf' in (output / 'report/sources.html').read_text()
    assert (output / exported[0]['snapshot_file']).read_bytes() == content


def test_missing_compiler_source_and_corrupt_payload_remain_explicit(
        modules, tmp_path):
    capture = importlib.import_module(modules[0].__package__ +
                                      '.source_capture')
    missing = tmp_path / 'missing.py'
    snapshots = capture.capture_metadata_sources(
        dict(source_file=str(missing), line=7, column=0))
    assert snapshots[0]['status'] == 'unavailable'
    assert snapshots[0]['reason'].startswith('FileNotFoundError:')
    corrupt = dict(status='captured',
                   sha256='0' * 64,
                   content=base64.b64encode(b'actual bytes').decode())
    with pytest.raises(ValueError, match='digest mismatch'):
        capture.export_metadata_sources([corrupt], tmp_path)
    assert not list(tmp_path.rglob('*.py'))
