"""Normal-installed provider admission; synthetic ELF is not device evidence."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from flagtree.debugger import gcu_native_analysis as analysis

spec = importlib.util.spec_from_file_location(
    'gcu_analysis_image_fixture',
    Path(__file__).with_name('test_gcu_native_image.py'))
image_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_fixture)


def inputs():
    binary, native = image_fixture.fixture()
    locations = dict(
        schema_version=1,
        marker_file='__flagprism_gcu_clock_v1__',
        locations=[dict(site_id=7, phase='end_counter', column=2, address=32)])
    return binary, native, locations, dict(sites=[dict(id=7)])


def test_synthetic_mapping_does_not_grant_boundary_or_reader_rights():
    binary, native, locations, manifest = inputs()
    report = analysis.analyze_native(binary,
                                     native,
                                     locations=locations,
                                     manifest=manifest)
    assert report['points'][0]['reader']['status'] == 'unverified'
    assert report['source_region_qualified'] is False
    assert report['reader_valueflow_qualified'] is False
    assert report['hardware_busy_qualified'] is False


@pytest.mark.parametrize('fault', [
    'schema_bool', 'foreign_site', 'phase', 'bool_address', 'duplicate_point',
    'wrong_bytes'
])
def test_analysis_rejects_mismatched_site_or_image(fault):
    binary, native, locations, manifest = inputs()
    locations = copy.deepcopy(locations)
    if fault == 'schema_bool':
        locations['schema_version'] = True
    elif fault == 'foreign_site':
        locations['locations'][0]['site_id'] = 8
    elif fault == 'phase':
        locations['locations'][0]['phase'] = 'begin_counter'
    elif fault == 'bool_address':
        locations['locations'][0]['address'] = True
    elif fault == 'duplicate_point':
        locations['locations'] *= 2
    else:
        native = native.replace(b'61 62 63 64', b'61 62 63 65')
    with pytest.raises(ValueError):
        analysis.analyze_native(binary,
                                native,
                                locations=locations,
                                manifest=manifest)


def test_analysis_budget_keeps_a_visible_unverified_point():
    binary, native, locations, manifest = inputs()
    with patch.object(analysis, 'time',
                      SimpleNamespace(monotonic=Mock(side_effect=[0, 11]))):
        report = analysis.analyze_native(binary,
                                         native,
                                         locations=locations,
                                         manifest=manifest)
    assert report['points'][0]['reader'][
        'reason'] == 'native_analysis_budget_exhausted'
    assert report['source_region_qualified'] is False
