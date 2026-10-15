"""Finalization measurements must not masquerade as shorter export phases."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture
def timing(monkeypatch):
    package = ModuleType('export_timing_under_test')
    package.__path__ = [str(Path(__file__).parents[1] / 'python/flagtree_profiler')]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    return importlib.import_module(package.__name__ + '.export_timing')


def bundle(tmp_path):
    (tmp_path / 'ai').mkdir()
    (tmp_path / 'manifest.json').write_text('{"files":{}}')
    return tmp_path


def test_api_complete_total_and_hash_include_collector_and_cleanup(timing, tmp_path):
    output = bundle(tmp_path)
    timing.finish_sessions([{'bundle_output': output, 'exported': True}], 5.75)
    path = output / 'ai/export_timing.json'
    data = json.loads(path.read_text())
    assert data['export_wall_s'] == 5.75
    assert data['complete_finalize_and_export'] is True
    assert data['phases'] == {'session_finalize_and_bundle_export_s': 5.75}
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['files']['ai/export_timing.json']['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_materialization_without_finalize_is_not_a_complete_cost(timing, tmp_path):
    data = timing.write_receipt(bundle(tmp_path), phases={'bundle_materialization_s': .1},
                                complete=False, scope='bundle_materialization_only')
    assert data['export_wall_s'] is None
    assert data['complete_finalize_and_export'] is False


def test_cli_uses_nonoverlapping_raw_finalize_then_export(timing, tmp_path):
    raw = tmp_path / 'capture'
    timing.finish_sessions([{'name': str(raw), 'exported': True}], 2.5)
    data = json.loads(raw.with_suffix('.finalization.json').read_text())
    assert data['collector_finalize_s'] == 2.5
    assert data['includes_bundle_export'] is False
    result = timing.write_receipt(bundle(tmp_path),
        phases={'collector_finalize_s': data['collector_finalize_s'], 'bundle_materialization_s': .25},
        complete=True, scope='collector_finalize_then_bundle_export')
    assert result['export_wall_s'] == 2.75


def test_failed_export_cannot_produce_complete_timing(timing, tmp_path):
    timing.finish_sessions([{'name': str(tmp_path / 'failed'), 'exported': False}], 1)
    assert not (tmp_path / 'failed.finalization.json').exists()


@pytest.mark.parametrize('value', [-1, float('nan'), True])
def test_invalid_phases_are_rejected(timing, tmp_path, value):
    with pytest.raises(ValueError, match='finite nonnegative'):
        timing.write_receipt(bundle(tmp_path), phases={'export': value}, complete=True, scope='test')
